from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _safe_float(value: Any) -> float:
    try:
        numeric = float(value)
    except Exception:
        return float("nan")
    if np.isnan(numeric):
        return float("nan")
    return numeric


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _artifact_exists(path: Any) -> bool:
    if not path:
        return False
    try:
        return Path(str(path)).exists()
    except Exception:
        return False


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


def build_study_validation_lock(
    results: dict,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    context = dict(report_context or {})
    study_design = results.get("study_design")
    study_name = getattr(study_design, "name", "PrimeVarClass Validation Lock")
    title = str(context.get("report_title") or f"{study_name} - Validation Lock")

    readiness_summary = dict((results.get("publication_readiness_assessment") or {}).get("summary") or {})
    comparative_summary = dict((results.get("comparative_evidence_assessment") or {}).get("summary") or {})
    independence_summary = dict((results.get("cohort_independence_assessment") or {}).get("summary") or {})
    baseline_summary = dict((results.get("baseline_coverage_assessment") or {}).get("summary") or {})
    claim_summary = dict((results.get("claim_strength_assessment") or {}).get("summary") or {})
    methods_summary = dict(results.get("methods_package_summary") or {})
    manuscript_summary = dict(results.get("manuscript_package_summary") or {})

    package_artifacts = [
        results.get("cohort_independence_manifest_path"),
        results.get("comparative_evidence_manifest_path"),
        results.get("claim_strength_manifest_path"),
        results.get("publication_readiness_manifest_path"),
        results.get("baseline_coverage_manifest_path"),
        results.get("methods_package_manifest_path"),
        results.get("manuscript_package_manifest_path"),
    ]
    artifact_bundle_percent = int(round(sum(1 for item in package_artifacts if _artifact_exists(item)) / len(package_artifacts) * 100)) if package_artifacts else 0

    claim_tier = str(claim_summary.get("claim_tier") or "insufficient")
    claim_tier_percent = {
        "strong": 100,
        "moderate": 82,
        "suggestive": 60,
        "insufficient": 30,
    }.get(claim_tier, 0)

    methods_reproducibility_percent = int(
        round(
            np.mean(
                [
                    100 if _artifact_exists(results.get("methods_package_manifest_path")) else 0,
                    100 if _artifact_exists(results.get("training_metrics_path")) else 0,
                    100 if _artifact_exists((results.get("model_paths") or {}).get("registry")) else 0,
                ]
            )
        )
    )
    manuscript_readiness_percent = int(
        round(
            np.mean(
                [
                    100 if _artifact_exists(results.get("manuscript_package_manifest_path")) else 0,
                    100 if _artifact_exists(results.get("manuscript_package_markdown_path")) else 0,
                    100 if manuscript_summary.get("best_external_experiment") else 0,
                ]
            )
        )
    )

    criteria = [
        _criterion_row(
            "cohort_independence",
            "Cohort independence lock",
            1.15,
            _safe_int(independence_summary.get("overall_independence_percent")),
            (
                f"Independencia entre coortes em {_safe_int(independence_summary.get('overall_independence_percent'))}% "
                f"com overlap maximo treino/externo de {_safe_int(independence_summary.get('max_variant_overlap_percent'))}%."
            ),
            "Preservar independencia total entre treino e validacao externa na release final.",
            critical=True,
        ),
        _criterion_row(
            "comparative_evidence",
            "Comparative evidence lock",
            1.25,
            _safe_int(comparative_summary.get("overall_comparative_strength_percent")),
            (
                f"Evidencia comparativa global em {_safe_int(comparative_summary.get('overall_comparative_strength_percent'))}% "
                f"com experimento lider {comparative_summary.get('best_supported_experiment') or '-'}."
            ),
            "Fortalecer a superioridade comparativa do candidato em mais coortes externas reais.",
            critical=True,
        ),
        _criterion_row(
            "claim_strength",
            "Claim strength lock",
            1.35,
            _safe_int(claim_summary.get("overall_claim_strength_percent")),
            (
                f"Claim tier {claim_tier} em {_safe_int(claim_summary.get('overall_claim_strength_percent'))}% "
                f"para {claim_summary.get('selected_experiment') or '-'}."
            ),
            "Elevar a forca da alegacao para um nivel moderado ou forte antes da submissao final.",
            critical=True,
        ),
        _criterion_row(
            "publication_readiness",
            "Publication readiness lock",
            1.3,
            _safe_int(readiness_summary.get("overall_readiness_percent")),
            (
                f"Publication readiness em {_safe_int(readiness_summary.get('overall_readiness_percent'))}% "
                f"com status {readiness_summary.get('overall_status') or '-'}."
            ),
            "Fechar os gaps criticos restantes do pacote de submissao.",
            critical=True,
        ),
        _criterion_row(
            "baseline_coverage",
            "Baseline and ablation lock",
            1.0,
            _safe_int(baseline_summary.get("overall_coverage_percent")),
            (
                f"Coverage de baseline/ablation em {_safe_int(baseline_summary.get('overall_coverage_percent'))}% "
                f"com melhor experimento primo {baseline_summary.get('best_prime_experiment') or '-'}."
            ),
            "Garantir que a narrativa de ablation e baseline esteja completa na rodada final.",
            critical=True,
        ),
        _criterion_row(
            "methods_reproducibility",
            "Methods reproducibility lock",
            0.95,
            methods_reproducibility_percent,
            (
                f"Reprodutibilidade metodologica em {methods_reproducibility_percent}% "
                f"com melhor experimento interno {methods_summary.get('best_internal_experiment') or '-'}."
            ),
            "Assegurar que metodos, metricas internas e registry acompanhem toda release.",
        ),
        _criterion_row(
            "manuscript_translation",
            "Manuscript and translational lock",
            0.9,
            int(round(np.mean([manuscript_readiness_percent, claim_tier_percent]))),
            (
                f"Pacote de manuscrito em {manuscript_readiness_percent}% e tier translacional da alegacao em {claim_tier_percent}%."
            ),
            "Usar um claim tier mais forte para sustentar narrativa translacional e de alto impacto.",
        ),
        _criterion_row(
            "artifact_bundle",
            "Validation artifact bundle",
            0.9,
            artifact_bundle_percent,
            f"{artifact_bundle_percent}% dos artefatos criticos de validacao foram materializados.",
            "Garantir manifests e relatorios de validacao para toda execucao candidata a release.",
        ),
    ]

    weighted_total = sum(float(item["weight"]) for item in criteria)
    weighted_score = sum(float(item["weight"]) * float(item["score_percent"]) for item in criteria)
    overall_percent = int(round(weighted_score / weighted_total)) if weighted_total else 0
    critical_gaps = [item["title"] for item in criteria if item["critical"] and item["score_percent"] < 70]
    recommended_actions = [item["next_step"] for item in criteria if item["score_percent"] < 85]

    ready_for_statistical_validation = bool(
        _safe_int(independence_summary.get("overall_independence_percent")) >= 90
        and _safe_int(comparative_summary.get("overall_comparative_strength_percent")) >= 60
        and _safe_int(claim_summary.get("overall_claim_strength_percent")) >= 55
        and _safe_int(baseline_summary.get("overall_coverage_percent")) >= 80
    )
    ready_for_submission_lock = bool(
        overall_percent >= 85
        and not critical_gaps
        and readiness_summary.get("ready_for_submission")
        and claim_tier in {"strong", "moderate"}
    )
    ready_for_translational_pilot = bool(
        overall_percent >= 80
        and claim_tier in {"strong", "moderate"}
        and bool(manuscript_summary.get("best_external_experiment"))
        and artifact_bundle_percent >= 85
    )

    summary = {
        "title": title,
        "generated_at": _now_utc(),
        "study_name": study_name,
        "overall_validation_lock_percent": overall_percent,
        "overall_status": _status_from_percent(overall_percent),
        "claim_tier": claim_tier,
        "ready_for_statistical_validation": ready_for_statistical_validation,
        "ready_for_submission_lock": ready_for_submission_lock,
        "ready_for_translational_pilot": ready_for_translational_pilot,
        "publication_readiness_percent": _safe_int(readiness_summary.get("overall_readiness_percent")),
        "comparative_evidence_percent": _safe_int(comparative_summary.get("overall_comparative_strength_percent")),
        "claim_strength_percent": _safe_int(claim_summary.get("overall_claim_strength_percent")),
        "cohort_independence_percent": _safe_int(independence_summary.get("overall_independence_percent")),
        "baseline_coverage_percent": _safe_int(baseline_summary.get("overall_coverage_percent")),
        "artifact_bundle_percent": artifact_bundle_percent,
        "n_critical_gaps": int(len(critical_gaps)),
    }

    markdown_lines = [
        f"# {title}",
        "",
        f"- Generated at: {summary['generated_at']}",
        f"- Overall validation lock: {summary['overall_validation_lock_percent']}%",
        f"- Claim tier: {summary['claim_tier']}",
        f"- Ready for statistical validation: {'yes' if summary['ready_for_statistical_validation'] else 'not yet'}",
        f"- Ready for submission lock: {'yes' if summary['ready_for_submission_lock'] else 'not yet'}",
        f"- Ready for translational pilot: {'yes' if summary['ready_for_translational_pilot'] else 'not yet'}",
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

    markdown_lines.extend(["## Lock Summary", ""])
    markdown_lines.extend(
        [
            f"- Publication readiness: {summary['publication_readiness_percent']}%",
            f"- Comparative evidence: {summary['comparative_evidence_percent']}%",
            f"- Claim strength: {summary['claim_strength_percent']}%",
            f"- Cohort independence: {summary['cohort_independence_percent']}%",
            f"- Baseline coverage: {summary['baseline_coverage_percent']}%",
            f"- Validation artifacts: {summary['artifact_bundle_percent']}%",
        ]
    )

    markdown_lines.extend(["", "## Recommended Actions", ""])
    if recommended_actions:
        for action in recommended_actions:
            markdown_lines.append(f"- {action}")
    else:
        markdown_lines.append("- O estudo parece pronto para consolidacao final.")

    return {
        "summary": summary,
        "criteria": criteria,
        "critical_gaps": critical_gaps,
        "recommended_actions": recommended_actions,
        "markdown_report": "\n".join(markdown_lines).strip(),
        "report_context": context,
    }


def build_study_validation_lock_html(bundle: dict) -> str:
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
        "<title>PrimeVarClass Validation Lock</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f7f2ea;color:#1b2730;max-width:1020px;margin:0 auto;padding:32px;line-height:1.68;}"
        "h1{font-size:2.2rem;}h2{margin-top:2rem;color:#874823;}h3{margin-top:1.35rem;color:#255b63;}"
        "ul{background:#fff;border:1px solid #e8dcc8;border-radius:16px;padding:18px 24px;}"
        "</style></head><body>"
        + "".join(blocks)
        + "</body></html>"
    )


def export_study_validation_lock(
    results: dict,
    output_dir: str,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    bundle = build_study_validation_lock(results, report_context=report_context)
    html_report = build_study_validation_lock_html(bundle)
    criteria_df = pd.DataFrame(bundle.get("criteria") or [])

    markdown_path = root / "study_validation_lock.md"
    html_path = root / "study_validation_lock.html"
    manifest_path = root / "study_validation_lock_manifest.json"
    criteria_path = root / "study_validation_lock_criteria.csv"

    markdown_path.write_text(str(bundle.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(html_report, encoding="utf-8")
    criteria_df.to_csv(criteria_path, index=False)

    manifest = {
        "generated_at": _now_utc(),
        "summary": bundle.get("summary"),
        "critical_gaps": bundle.get("critical_gaps"),
        "recommended_actions": bundle.get("recommended_actions"),
        "report_context": bundle.get("report_context"),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "criteria_path": str(criteria_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "study_validation_lock": bundle,
        "study_validation_lock_markdown_path": str(markdown_path),
        "study_validation_lock_html_path": str(html_path),
        "study_validation_lock_manifest_path": str(manifest_path),
        "study_validation_lock_criteria_path": str(criteria_path),
    }
