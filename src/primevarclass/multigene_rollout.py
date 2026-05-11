from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _load_json(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    candidate = Path(path)
    if not candidate.exists():
        raise FileNotFoundError(f"Manifesto nao encontrado: {path}")
    return json.loads(candidate.read_text(encoding="utf-8"))


def _normalize_candidates(gene_expansion_manifest: dict[str, Any]) -> pd.DataFrame:
    candidates = pd.DataFrame(gene_expansion_manifest.get("top_candidates", []))
    if candidates.empty:
        return pd.DataFrame(
            columns=[
                "gene",
                "expansion_priority_percent",
                "priority_band",
                "clinvar_labeled_rows",
                "clinvar_expert_rows",
                "mavedb_score_set_count",
                "mavedb_score_rows",
                "gnomad_direct_api_ready",
            ]
        )
    sort_columns = [column for column in ["expansion_priority_percent", "clinvar_expert_rows", "mavedb_score_rows"] if column in candidates.columns]
    return candidates.sort_values(sort_columns, ascending=[False] * len(sort_columns)).reset_index(drop=True)


def _phase_for_candidate(priority_band: str, rank_index: int, max_phase_1: int, max_phase_2: int) -> str:
    normalized_band = str(priority_band or "").strip().lower()
    if normalized_band == "ready" and rank_index < max_phase_1:
        return "phase_1_immediate"
    if normalized_band in {"ready", "strong"} and rank_index < max_phase_1 + max_phase_2:
        return "phase_2_expansion"
    return "phase_3_exploration"


def build_multigene_rollout_plan(
    gene_expansion_manifest_path: str,
    prime_intelligence_manifest_path: str | None = None,
    max_phase_1: int = 3,
    max_phase_2: int = 4,
    max_total_genes: int = 10,
) -> dict[str, Any]:
    gene_expansion_manifest = _load_json(gene_expansion_manifest_path)
    prime_intelligence_manifest = _load_json(prime_intelligence_manifest_path)

    candidates = _normalize_candidates(gene_expansion_manifest).head(max_total_genes).copy()
    prime_summary = prime_intelligence_manifest.get("summary", {})
    prime_top_gene = str(prime_summary.get("top_candidate_gene_beyond_brca") or "").strip().upper() or None
    prime_runway_percent = int(round(float(prime_summary.get("cross_gene_runway_percent", 0) or 0)))
    prime_alignment_percent = int(round(float(prime_summary.get("prime_biological_alignment_percent", 0) or 0)))

    if candidates.empty:
        summary = {
            "generated_at": _now_utc(),
            "overall_rollout_readiness_percent": 0,
            "phase_1_gene_count": 0,
            "phase_2_gene_count": 0,
            "phase_3_gene_count": 0,
            "phase_1_genes": [],
            "phase_2_genes": [],
            "phase_3_genes": [],
            "prime_top_candidate_gene": prime_top_gene,
            "cross_gene_runway_percent": prime_runway_percent,
            "prime_biological_alignment_percent": prime_alignment_percent,
        }
        return {
            "summary": summary,
            "recommended_actions": [
                "Gerar ou fornecer um gene_expansion_manifest.json antes de planejar a rodada multigenica."
            ],
            "rollout_table": pd.DataFrame(),
            "report_context": {
                "gene_expansion_manifest_path": str(Path(gene_expansion_manifest_path).resolve()),
                "prime_intelligence_manifest_path": str(Path(prime_intelligence_manifest_path).resolve()) if prime_intelligence_manifest_path else None,
            },
        }

    rollout_rows: list[dict[str, Any]] = []
    for rank_index, row in candidates.reset_index(drop=True).iterrows():
        gene = str(row.get("gene", "")).strip().upper()
        phase = _phase_for_candidate(
            priority_band=str(row.get("priority_band", "")),
            rank_index=rank_index,
            max_phase_1=max_phase_1,
            max_phase_2=max_phase_2,
        )
        prime_priority = "high" if gene == prime_top_gene or rank_index < max_phase_1 else "medium"
        training_strategy = (
            "full_multicohort_train_plus_external_validation"
            if phase == "phase_1_immediate"
            else "staged_training_then_external_lock"
        )
        rollout_rows.append(
            {
                "gene": gene,
                "rank": int(rank_index + 1),
                "rollout_phase": phase,
                "expansion_priority_percent": float(row.get("expansion_priority_percent", 0.0)),
                "priority_band": str(row.get("priority_band", "")),
                "clinvar_labeled_rows": int(row.get("clinvar_labeled_rows", 0) or 0),
                "clinvar_expert_rows": int(row.get("clinvar_expert_rows", 0) or 0),
                "mavedb_score_set_count": int(row.get("mavedb_score_set_count", 0) or 0),
                "mavedb_score_rows": int(row.get("mavedb_score_rows", 0) or 0),
                "gnomad_direct_api_ready": bool(row.get("gnomad_direct_api_ready", False)),
                "prime_priority": prime_priority,
                "training_strategy": training_strategy,
                "recommended_validation_stack": "clinical_holdout + functional_assay + population_annotations",
            }
        )

    rollout_table = pd.DataFrame(rollout_rows)
    phase_1_genes = rollout_table.loc[rollout_table["rollout_phase"] == "phase_1_immediate", "gene"].tolist()
    phase_2_genes = rollout_table.loc[rollout_table["rollout_phase"] == "phase_2_expansion", "gene"].tolist()
    phase_3_genes = rollout_table.loc[rollout_table["rollout_phase"] == "phase_3_exploration", "gene"].tolist()
    top_priority = float(rollout_table["expansion_priority_percent"].head(max_phase_1 + max_phase_2).mean())
    overall_rollout_readiness = int(round((top_priority * 0.7) + (prime_runway_percent * 0.2) + (prime_alignment_percent * 0.1)))

    return {
        "summary": {
            "generated_at": _now_utc(),
            "overall_rollout_readiness_percent": overall_rollout_readiness,
            "phase_1_gene_count": int(len(phase_1_genes)),
            "phase_2_gene_count": int(len(phase_2_genes)),
            "phase_3_gene_count": int(len(phase_3_genes)),
            "phase_1_genes": phase_1_genes,
            "phase_2_genes": phase_2_genes,
            "phase_3_genes": phase_3_genes,
            "prime_top_candidate_gene": prime_top_gene,
            "cross_gene_runway_percent": prime_runway_percent,
            "prime_biological_alignment_percent": prime_alignment_percent,
        },
        "recommended_actions": [
            "Abrir a proxima rodada real pelos genes da phase_1 com treino multicohorte e holdouts externos separados.",
            "Usar o bloco de numeros primos como eixo explicativo priorizando o gene mais alinhado ao prime-intelligence.",
            "Reservar os genes da phase_2 para expansao logo apos estabilizar os manifests reais da phase_1.",
        ],
        "rollout_table": rollout_table,
        "report_context": {
            "gene_expansion_manifest_path": str(Path(gene_expansion_manifest_path).resolve()),
            "prime_intelligence_manifest_path": str(Path(prime_intelligence_manifest_path).resolve()) if prime_intelligence_manifest_path else None,
        },
    }


def _build_rollout_markdown(assessment: dict[str, Any]) -> str:
    summary = assessment["summary"]
    rollout_table = assessment["rollout_table"]
    lines = [
        "# PrimeVarClass Multigene Rollout",
        "",
        f"- Generated at: `{summary['generated_at']}`",
        f"- Overall rollout readiness: `{summary['overall_rollout_readiness_percent']}%`",
        f"- Phase 1 genes: `{', '.join(summary['phase_1_genes']) if summary['phase_1_genes'] else 'none'}`",
        f"- Phase 2 genes: `{', '.join(summary['phase_2_genes']) if summary['phase_2_genes'] else 'none'}`",
        f"- Prime top candidate gene: `{summary.get('prime_top_candidate_gene') or 'n/a'}`",
        "",
        "## Recommended Actions",
    ]
    for action in assessment["recommended_actions"]:
        lines.append(f"- {action}")
    if rollout_table.empty:
        table_markdown = "_No genes selected._"
    else:
        header = "| " + " | ".join(str(column) for column in rollout_table.columns) + " |"
        divider = "| " + " | ".join("---" for _ in rollout_table.columns) + " |"
        body = [
            "| " + " | ".join(str(value) for value in row) + " |"
            for row in rollout_table.itertuples(index=False, name=None)
        ]
        table_markdown = "\n".join([header, divider, *body])
    lines.extend(["", "## Rollout Table", "", table_markdown])
    return "\n".join(lines)


def export_multigene_rollout_plan(
    gene_expansion_manifest_path: str,
    output_dir: str = "primevarclass_multigene_rollout_results",
    prime_intelligence_manifest_path: str | None = None,
    max_phase_1: int = 3,
    max_phase_2: int = 4,
    max_total_genes: int = 10,
) -> dict[str, Any]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    assessment = build_multigene_rollout_plan(
        gene_expansion_manifest_path=gene_expansion_manifest_path,
        prime_intelligence_manifest_path=prime_intelligence_manifest_path,
        max_phase_1=max_phase_1,
        max_phase_2=max_phase_2,
        max_total_genes=max_total_genes,
    )
    rollout_table = assessment.pop("rollout_table")
    rollout_csv_path = output_root / "multigene_rollout_plan.csv"
    markdown_path = output_root / "multigene_rollout_plan.md"
    html_path = output_root / "multigene_rollout_plan.html"
    manifest_path = output_root / "multigene_rollout_manifest.json"

    rollout_table.to_csv(rollout_csv_path, index=False)
    markdown = _build_rollout_markdown({**assessment, "rollout_table": rollout_table})
    markdown_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(f"<html><body><pre>{markdown}</pre></body></html>", encoding="utf-8")

    manifest = {
        "generated_at": assessment["summary"]["generated_at"],
        "summary": assessment["summary"],
        "recommended_actions": assessment["recommended_actions"],
        "report_context": assessment["report_context"],
        "rollout_csv_path": str(rollout_csv_path.resolve()),
        "markdown_path": str(markdown_path.resolve()),
        "html_path": str(html_path.resolve()),
        "manifest_path": str(manifest_path.resolve()),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
