from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .data_sources import load_source_catalog
from .public_sources import build_public_source_catalog_assessment


PLACEHOLDER_TOKENS = {"yyyy-mm-dd", "vx.y", "urn:mavedb:..."}


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _normalize_token(value: Any) -> str:
    return str(value or "").strip().lower()


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _status_from_percent(value: int) -> str:
    if value >= 85:
        return "ready"
    if value >= 60:
        return "partial"
    return "gap"


def _criterion_row(
    criterion_id: str,
    title: str,
    weight: float,
    score_percent: int,
    evidence: str,
    next_step: str,
    critical: bool = False,
) -> dict:
    normalized = max(0, min(100, int(score_percent)))
    return {
        "criterion_id": criterion_id,
        "title": title,
        "weight": float(weight),
        "score_percent": normalized,
        "status": _status_from_percent(normalized),
        "critical": bool(critical),
        "evidence": evidence,
        "next_step": next_step,
    }


def _resolve_source_config_path(study_config_path: str, source_config: str) -> Path:
    candidate = Path(source_config)
    if candidate.is_absolute():
        return candidate.resolve()
    root_relative = (Path.cwd() / candidate).resolve()
    if root_relative.exists():
        return root_relative
    return (Path(study_config_path).resolve().parent / candidate).resolve()


def _resolve_path(path_value: str | None, *, config_dir: Path) -> Path | None:
    if not path_value:
        return None
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate.resolve()
    cwd_candidate = candidate.resolve()
    if cwd_candidate.exists():
        return cwd_candidate
    return (config_dir / candidate).resolve()


def _is_example_path(path: Path | None) -> bool:
    if path is None:
        return False
    lowered = _normalize_token(path.as_posix())
    name = _normalize_token(path.name)
    return "/data/examples/" in lowered or name.startswith("example") or "_like_" in name or "example" in name


def _is_raw_data_path(path: Path | None) -> bool:
    if path is None:
        return False
    lowered = _normalize_token(path.as_posix())
    return "/data/raw/" in lowered


def _is_placeholder_release(value: Any) -> bool:
    token = _normalize_token(value)
    if not token:
        return True
    if token in PLACEHOLDER_TOKENS:
        return True
    return "..." in token


def _assessment_index(assessment: dict | None) -> dict[str, dict]:
    return {
        str(item.get("source_name") or ""): dict(item)
        for item in (assessment or {}).get("sources", [])
        if str(item.get("source_name") or "")
    }


def build_cohort_freeze_assessment(*, config_path: str, cohort_name: str, cohort_role: str) -> dict:
    config_file = Path(config_path).resolve()
    config_dir = config_file.parent
    catalog = load_source_catalog(str(config_file))
    public_assessment = build_public_source_catalog_assessment(
        config_path=str(config_file),
        catalog=catalog,
        source_provenance=[],
    )
    public_index = _assessment_index(public_assessment)

    source_rows: List[dict] = []
    criteria_inputs: List[dict] = []

    for spec in catalog.sources:
        public_row = public_index.get(spec.name, {})
        recognized_public = bool(public_row.get("recognized_public_source"))
        resolved_path = _resolve_path(spec.path, config_dir=config_dir) if str(spec.source_type or "file").lower() == "file" else None
        path_exists = bool(resolved_path and resolved_path.exists())
        example_path = _is_example_path(resolved_path)
        raw_data_path = _is_raw_data_path(resolved_path)
        release_value = public_row.get("release_value") or spec.release_version or spec.release_date
        placeholder_release = recognized_public and _is_placeholder_release(release_value)
        concrete_release = recognized_public and not placeholder_release
        ready_for_real_data_source = bool(path_exists and not example_path and (not recognized_public or concrete_release))

        evidence_score = int(
            round(
                np.mean(
                    [
                        100 if path_exists else 0,
                        0 if example_path else 100,
                        100 if (not recognized_public or concrete_release) else 20,
                    ]
                )
            )
        )

        if not path_exists:
            recommendation = "Informar um arquivo local existente para esta fonte antes de congelar a coorte."
        elif example_path:
            recommendation = "Substituir o arquivo de exemplo por um dataset publico real e versionado."
        elif recognized_public and placeholder_release:
            recommendation = "Preencher release_version/release_date reais para sustentar rastreabilidade cientifica."
        else:
            recommendation = "Fonte apta para congelamento cientifico da coorte."

        row = {
            "cohort_name": cohort_name,
            "cohort_role": cohort_role,
            "source_name": spec.name,
            "kind": spec.kind,
            "source_type": spec.source_type,
            "preset": spec.preset,
            "recognized_public_source": recognized_public,
            "resolved_path": str(resolved_path) if resolved_path is not None else None,
            "path_exists": path_exists,
            "uses_example_path": example_path,
            "uses_raw_data_path": raw_data_path,
            "release_value": release_value,
            "has_placeholder_release": placeholder_release,
            "has_concrete_release": concrete_release,
            "ready_for_real_data_source": ready_for_real_data_source,
            "source_real_data_percent": evidence_score,
            "recommended_action": recommendation,
        }
        source_rows.append(row)
        criteria_inputs.append(row)

    source_table = pd.DataFrame(source_rows)
    recognized_table = source_table[source_table["recognized_public_source"] == True].copy() if not source_table.empty else pd.DataFrame()
    missing_count = int((source_table["path_exists"] == False).sum()) if not source_table.empty else 0
    existing_count = int((source_table["path_exists"] == True).sum()) if not source_table.empty else 0
    example_count = int((source_table["uses_example_path"] == True).sum()) if not source_table.empty else 0
    placeholder_count = int((source_table["has_placeholder_release"] == True).sum()) if not source_table.empty else 0
    raw_count = int((source_table["uses_raw_data_path"] == True).sum()) if not source_table.empty else 0
    ready_count = int((source_table["ready_for_real_data_source"] == True).sum()) if not source_table.empty else 0
    overall_percent = int(round(source_table["source_real_data_percent"].mean())) if not source_table.empty else 0
    public_release_percent = int(round(recognized_table["has_concrete_release"].mean() * 100)) if not recognized_table.empty else 0
    real_source_percent = int(round(source_table["ready_for_real_data_source"].mean() * 100)) if not source_table.empty else 0

    criteria = [
        _criterion_row(
            "existing_paths",
            "Existing local paths",
            1.05,
            int(round(source_table["path_exists"].mean() * 100)) if not source_table.empty else 0,
            f"{existing_count}/{len(source_table)} fontes possuem caminho existente." if not source_table.empty else "Nenhuma fonte encontrada.",
            "Garantir que todos os arquivos de entrada estejam presentes no workspace antes do freeze final.",
            critical=True,
        ),
        _criterion_row(
            "no_example_sources",
            "No example/demo sources",
            1.3,
            int(round((1 - source_table["uses_example_path"].mean()) * 100)) if not source_table.empty else 0,
            f"{example_count} fonte(s) ainda apontam para dados de exemplo/demo.",
            "Remover arquivos de exemplo do estudo final antes da rodada real.",
            critical=True,
        ),
        _criterion_row(
            "public_release_concreteness",
            "Concrete public releases",
            1.2,
            public_release_percent,
            f"{placeholder_count} fonte(s) publicas ainda usam release placeholder.",
            "Trocar placeholders por release_version/release_date reais para ClinVar, gnomAD, MaveDB e ENIGMA.",
            critical=True,
        ),
        _criterion_row(
            "real_data_source_ready",
            "Real-data source readiness",
            1.35,
            real_source_percent,
            f"{ready_count}/{len(source_table)} fontes estao aptas para congelamento cientifico." if not source_table.empty else "Nenhuma fonte encontrada.",
            "Substituir demos por dados reais e manter apenas fontes congeladas para o benchmark final.",
            critical=True,
        ),
        _criterion_row(
            "raw_data_staging",
            "Raw-data staging footprint",
            0.75,
            int(round(raw_count / len(source_table) * 100)) if not source_table.empty else 0,
            f"{raw_count} fonte(s) apontam para staging de dados brutos em data/raw.",
            "Preferir staging em data/raw ou artefatos resolvidos versionados para coortes finais.",
        ),
    ]

    weighted_total = sum(float(item["weight"]) for item in criteria)
    weighted_score = sum(float(item["weight"]) * float(item["score_percent"]) for item in criteria)
    freeze_percent = int(round(weighted_score / weighted_total)) if weighted_total else 0
    critical_gaps = [item["title"] for item in criteria if item["critical"] and item["score_percent"] < 70]
    recommended_actions = [item["next_step"] for item in criteria if item["score_percent"] < 85]

    summary = {
        "cohort_name": cohort_name,
        "cohort_role": cohort_role,
        "config_path": str(config_file),
        "overall_real_data_readiness_percent": freeze_percent,
        "overall_status": _status_from_percent(freeze_percent),
        "n_sources": int(len(source_table)),
        "n_recognized_public_sources": int(len(recognized_table)),
        "n_ready_real_sources": ready_count,
        "n_missing_sources": missing_count,
        "n_example_sources": example_count,
        "n_placeholder_release_sources": placeholder_count,
        "n_raw_data_sources": raw_count,
        "ready_for_real_data_lock": bool(not source_table.empty and missing_count == 0 and example_count == 0 and placeholder_count == 0),
    }

    markdown_lines = [
        f"# Cohort Freeze Audit - {cohort_name}",
        "",
        f"- Cohort role: {cohort_role}",
        f"- Config path: {summary['config_path']}",
        f"- Real-data readiness: {summary['overall_real_data_readiness_percent']}%",
        f"- Ready for real-data lock: {'yes' if summary['ready_for_real_data_lock'] else 'not yet'}",
        "",
        "## Criteria",
        "",
    ]
    for item in criteria:
        markdown_lines.extend(
            [
                f"### {item['title']}",
                "",
                f"- Score: {item['score_percent']}%",
                f"- Status: {item['status']}",
                f"- Critical: {'yes' if item['critical'] else 'no'}",
                f"- Evidence: {item['evidence']}",
                f"- Next step: {item['next_step']}",
                "",
            ]
        )

    markdown_lines.extend(["## Sources", ""])
    for row in source_rows:
        markdown_lines.append(
            f"- {row['source_name']}: ready={'yes' if row['ready_for_real_data_source'] else 'no'} | "
            f"example={'yes' if row['uses_example_path'] else 'no'} | "
            f"placeholder_release={'yes' if row['has_placeholder_release'] else 'no'} | "
            f"path={row['resolved_path'] or '-'}"
        )

    return {
        "summary": summary,
        "criteria": criteria,
        "critical_gaps": critical_gaps,
        "recommended_actions": recommended_actions,
        "sources": source_rows,
        "markdown_report": "\n".join(markdown_lines).strip(),
    }


def build_cohort_freeze_html(bundle: dict) -> str:
    markdown = str(bundle.get("markdown_report") or "")
    blocks: List[str] = []
    for block in markdown.split("\n\n"):
        stripped = block.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            blocks.append(f"<h1>{html.escape(stripped[2:])}</h1>")
            continue
        if stripped.startswith("## "):
            blocks.append(f"<h2>{html.escape(stripped[3:])}</h2>")
            continue
        if stripped.startswith("### "):
            blocks.append(f"<h3>{html.escape(stripped[4:])}</h3>")
            continue
        if stripped.startswith("- "):
            items = "".join(f"<li>{html.escape(line[2:])}</li>" for line in stripped.splitlines() if line.startswith("- "))
            blocks.append(f"<ul>{items}</ul>")
            continue
        blocks.append(f"<p>{html.escape(stripped)}</p>")
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>PrimeVarClass Cohort Freeze Audit</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f7f3eb;color:#17242f;max-width:980px;margin:0 auto;padding:32px;line-height:1.68;}"
        "h1{font-size:2.2rem;}h2{margin-top:2rem;color:#8b4b2a;}h3{margin-top:1.35rem;color:#2d6f73;}"
        "ul{background:#fff;border:1px solid #eadfcf;border-radius:16px;padding:18px 24px;}"
        "</style></head><body>"
        + "".join(blocks)
        + "</body></html>"
    )


def export_study_cohort_freeze(*, config_path: str, output_dir: str) -> dict:
    from .study import load_study_design

    study = load_study_design(config_path)
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    cohort_rows: List[dict] = []
    source_rows: List[dict] = []
    recommended_actions: List[str] = []

    for cohort in study.cohorts or []:
        resolved_source_config = _resolve_source_config_path(config_path, cohort.source_config)
        bundle = build_cohort_freeze_assessment(
            config_path=str(resolved_source_config),
            cohort_name=cohort.name,
            cohort_role=cohort.role,
        )
        cohort_summary = dict(bundle.get("summary") or {})
        cohort_rows.append(cohort_summary)
        source_rows.extend(bundle.get("sources") or [])
        recommended_actions.extend(bundle.get("recommended_actions") or [])

    cohorts_df = pd.DataFrame(cohort_rows)
    sources_df = pd.DataFrame(source_rows)
    overall_percent = int(round(cohorts_df["overall_real_data_readiness_percent"].mean())) if not cohorts_df.empty else 0
    ready_mask = cohorts_df["ready_for_real_data_lock"] == True if not cohorts_df.empty else pd.Series(dtype=bool)
    example_blocked = int((cohorts_df["n_example_sources"] > 0).sum()) if not cohorts_df.empty else 0
    placeholder_blocked = int((cohorts_df["n_placeholder_release_sources"] > 0).sum()) if not cohorts_df.empty else 0

    summary = {
        "generated_at": _now_utc(),
        "config_path": str(Path(config_path).resolve()),
        "study_name": study.name,
        "n_cohorts": int(len(cohorts_df)),
        "n_ready_cohorts": int(ready_mask.sum()) if not cohorts_df.empty else 0,
        "n_example_blocked_cohorts": example_blocked,
        "n_placeholder_release_blocked_cohorts": placeholder_blocked,
        "overall_real_data_readiness_percent": overall_percent,
        "overall_status": _status_from_percent(overall_percent),
        "ready_for_real_data_study": bool(not cohorts_df.empty and bool(ready_mask.all())),
    }

    critical_gaps: List[str] = []
    if example_blocked:
        critical_gaps.append("Example/demo sources still present")
    if placeholder_blocked:
        critical_gaps.append("Placeholder public releases still present")
    if not summary["ready_for_real_data_study"]:
        recommended_actions.append("Congelar cada coorte apenas com dados reais versionados antes do benchmark final.")

    markdown_lines = [
        "# Study Cohort Freeze",
        "",
        f"- Generated at: {summary['generated_at']}",
        f"- Study: {summary['study_name']}",
        f"- Real-data readiness: {summary['overall_real_data_readiness_percent']}%",
        f"- Ready for real-data study: {'yes' if summary['ready_for_real_data_study'] else 'not yet'}",
        f"- Ready cohorts: {summary['n_ready_cohorts']}/{summary['n_cohorts']}",
        "",
        "## Cohorts",
        "",
    ]
    for row in cohort_rows:
        markdown_lines.append(
            f"- {row['cohort_name']} ({row['cohort_role']}): "
            f"{row['overall_real_data_readiness_percent']}% | "
            f"example={row['n_example_sources']} | placeholder_release={row['n_placeholder_release_sources']} | "
            f"ready={'yes' if row['ready_for_real_data_lock'] else 'no'}"
        )

    markdown_lines.extend(["", "## Recommended Actions", ""])
    for action in dict.fromkeys(recommended_actions):
        markdown_lines.append(f"- {action}")

    bundle = {
        "summary": summary,
        "critical_gaps": critical_gaps,
        "recommended_actions": list(dict.fromkeys(recommended_actions)),
        "cohorts": cohort_rows,
        "sources": source_rows,
        "markdown_report": "\n".join(markdown_lines).strip(),
    }
    html_report = build_cohort_freeze_html(bundle)

    markdown_path = root / "study_cohort_freeze_report.md"
    html_path = root / "study_cohort_freeze_report.html"
    manifest_path = root / "study_cohort_freeze_manifest.json"
    cohorts_path = root / "study_cohort_freeze_cohorts.csv"
    sources_path = root / "study_cohort_freeze_sources.csv"

    markdown_path.write_text(bundle["markdown_report"], encoding="utf-8")
    html_path.write_text(html_report, encoding="utf-8")
    cohorts_df.to_csv(cohorts_path, index=False)
    sources_df.to_csv(sources_path, index=False)

    manifest = {
        "generated_at": summary["generated_at"],
        "summary": summary,
        "critical_gaps": critical_gaps,
        "recommended_actions": bundle["recommended_actions"],
        "cohorts_path": str(cohorts_path),
        "sources_path": str(sources_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "study_cohort_freeze": bundle,
        "study_cohort_freeze_summary": summary,
        "study_cohort_freeze_manifest_path": str(manifest_path),
        "study_cohort_freeze_markdown_path": str(markdown_path),
        "study_cohort_freeze_html_path": str(html_path),
        "study_cohort_freeze_cohorts_path": str(cohorts_path),
        "study_cohort_freeze_sources_path": str(sources_path),
    }
