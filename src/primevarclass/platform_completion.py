from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


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


def build_platform_completion_assessment(
    *,
    roadmap: dict,
    evidence_summary: Dict[str, Any] | None = None,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    context = dict(report_context or {})
    roadmap_summary = dict((roadmap or {}).get("summary") or {})
    stages = list((roadmap or {}).get("stages") or [])
    evidence = dict(evidence_summary or {})

    development_percent = _safe_int(roadmap_summary.get("overall_progress_percent"))
    evidence_percent = int(
        round(
            sum(
                [
                    _safe_int(evidence.get("real_data_readiness_percent")),
                    _safe_int(evidence.get("comparative_evidence_percent")),
                    _safe_int(evidence.get("claim_strength_percent")),
                    _safe_int(evidence.get("publication_readiness_percent")),
                    _safe_int(evidence.get("translational_impact_percent")),
                ]
            )
            / 5
        )
    ) if evidence else 0

    scientific_validation_pending = True
    if evidence:
        scientific_validation_pending = not bool(
            evidence.get("ready_for_submission_lock")
            and evidence.get("ready_for_shadow_rollout")
            and evidence.get("ready_for_real_data_study")
        )

    summary = {
        "generated_at": _now_utc(),
        "overall_platform_completion_percent": development_percent,
        "overall_platform_status": _status_from_percent(development_percent),
        "development_complete": bool(development_percent >= 100),
        "n_completed_stages": _safe_int(roadmap_summary.get("completed_stages")),
        "n_total_stages": int(len(stages)),
        "scientific_validation_pending": scientific_validation_pending,
        "evidence_execution_percent": evidence_percent,
        "evidence_execution_status": _status_from_percent(evidence_percent),
        "evidence_execution_tracked": bool(evidence),
        "ready_for_live_scientific_closeout": bool(
            evidence
            and not scientific_validation_pending
        ),
    }

    recommended_actions: List[str] = []
    if summary["development_complete"]:
        recommended_actions.append("Desenvolvimento da plataforma concluido; usar o fluxo publico final com coortes reais para fechar a validacao cientifica.")
    if summary["scientific_validation_pending"]:
        recommended_actions.append("Executar a rodada final com dados reais versionados para elevar comparative evidence, claim strength e real-data readiness.")
    if not summary["evidence_execution_tracked"]:
        recommended_actions.append("Carregar um estudo real exportado para registrar o estado de evidencia em dados reais.")

    markdown_lines = [
        "# PrimeVarClass - Platform Completion",
        "",
        f"- Generated at: {summary['generated_at']}",
        f"- Platform development completion: {summary['overall_platform_completion_percent']}%",
        f"- Development complete: {'yes' if summary['development_complete'] else 'not yet'}",
        f"- Completed stages: {summary['n_completed_stages']}/{summary['n_total_stages']}",
        f"- Scientific validation pending: {'yes' if summary['scientific_validation_pending'] else 'no'}",
        f"- Evidence execution tracked: {'yes' if summary['evidence_execution_tracked'] else 'not yet'}",
        f"- Evidence execution percent: {summary['evidence_execution_percent']}%",
        "",
        "## Truth Guardrail",
        "",
        "- Este pacote fecha o desenvolvimento da plataforma como produto e infraestrutura cientifica.",
        "- Ele nao declara, por si so, que a tese cientifica ja foi validada em coortes reais finais.",
        "- A validacao final continua sendo medida separadamente pelos artefatos de comparative evidence, claim strength e publication readiness.",
        "",
        "## Recommended Actions",
        "",
    ]
    for action in recommended_actions:
        markdown_lines.append(f"- {action}")

    return {
        "summary": summary,
        "recommended_actions": recommended_actions,
        "roadmap_summary": roadmap_summary,
        "evidence_summary": evidence,
        "report_context": context,
        "markdown_report": "\n".join(markdown_lines).strip(),
    }


def build_platform_completion_html(bundle: dict) -> str:
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
        if stripped.startswith("- "):
            items = "".join(f"<li>{html.escape(line[2:])}</li>" for line in stripped.splitlines() if line.startswith("- "))
            blocks.append(f"<ul>{items}</ul>")
            continue
        blocks.append(f"<p>{html.escape(stripped)}</p>")
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>PrimeVarClass Platform Completion</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f7f2ea;color:#1a2832;max-width:980px;margin:0 auto;padding:32px;line-height:1.68;}"
        "h1{font-size:2.2rem;}h2{margin-top:2rem;color:#8c4f2d;}ul{background:#fff;border:1px solid #e7dccb;border-radius:16px;padding:18px 24px;}"
        "</style></head><body>"
        + "".join(blocks)
        + "</body></html>"
    )


def export_platform_completion_assessment(
    *,
    roadmap: dict,
    output_dir: str,
    evidence_summary: Dict[str, Any] | None = None,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    bundle = build_platform_completion_assessment(
        roadmap=roadmap,
        evidence_summary=evidence_summary,
        report_context=report_context,
    )

    markdown_path = root / "platform_completion.md"
    html_path = root / "platform_completion.html"
    manifest_path = root / "platform_completion_manifest.json"

    markdown_path.write_text(str(bundle.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(build_platform_completion_html(bundle), encoding="utf-8")

    manifest = {
        "generated_at": _now_utc(),
        "summary": bundle.get("summary"),
        "recommended_actions": bundle.get("recommended_actions"),
        "roadmap_summary": bundle.get("roadmap_summary"),
        "evidence_summary": bundle.get("evidence_summary"),
        "report_context": bundle.get("report_context"),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "platform_completion": bundle,
        "platform_completion_summary": bundle.get("summary") or {},
        "platform_completion_markdown_path": str(markdown_path),
        "platform_completion_html_path": str(html_path),
        "platform_completion_manifest_path": str(manifest_path),
    }
