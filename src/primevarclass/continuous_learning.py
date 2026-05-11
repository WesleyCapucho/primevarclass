from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .data_sources import ingest_sources_from_config
from .public_bootstrap import (
    build_public_benchmark_readiness,
    build_public_source_bootstrap_bundle,
    load_public_source_sync_history,
)
from .public_sync import SYNC_RECIPES


CONNECTOR_BLUEPRINTS: dict[str, dict[str, str]] = {
    "clinvar": {
        "training_role": "clinical supervision and label refresh",
        "refresh_cadence": "weekly detection with monthly frozen benchmark snapshots",
        "promotion_gate": "never promote directly from live updates; require locked benchmark rerun",
        "scientific_value": "core pathogenicity supervision with review metadata",
    },
    "mavedb": {
        "training_role": "functional assay enrichment and calibration",
        "refresh_cadence": "per public score-set release or twice-yearly bulk refresh",
        "promotion_gate": "promote only after overlapping-gene benchmark holds or improves",
        "scientific_value": "functional effect evidence for mechanistic and gene-specialist models",
    },
    "gnomad": {
        "training_role": "population rarity and background constraint annotation",
        "refresh_cadence": "per release; refresh annotations without changing labels",
        "promotion_gate": "annotation-only refresh can go live; model promotion still requires benchmark lock",
        "scientific_value": "population baseline and rarity control for calibration",
    },
    "enigma": {
        "training_role": "expert-panel BRCA curation",
        "refresh_cadence": "manual frozen refresh when a curated release is staged",
        "promotion_gate": "always freeze and audit before external benchmark or publication claims",
        "scientific_value": "high-trust BRCA adjudication for credibility and adjudication checks",
    },
    "uniprot": {
        "training_role": "sequence, domain, and protein-function annotation",
        "refresh_cadence": "monthly or per targeted gene refresh",
        "promotion_gate": "annotation-only until structural and performance checks pass",
        "scientific_value": "protein context and accession backbone for structural modules",
    },
    "alphafold_db": {
        "training_role": "predicted structural context for mutant modeling",
        "refresh_cadence": "per accession/model refresh after accession mapping lock",
        "promotion_gate": "never alone; use as structural enrichment for protein and quantum modules",
        "scientific_value": "3D coordinate prior for residue environment and quantum targeting",
    },
    "pdb": {
        "training_role": "experimental structure validation overlay",
        "refresh_cadence": "targeted refresh for prioritized genes and residues",
        "promotion_gate": "validation overlay only; do not treat as label supervision",
        "scientific_value": "experimental structural evidence and local geometry support",
    },
    "civic": {
        "training_role": "translational evidence and actionability prioritization",
        "refresh_cadence": "monthly or per project review cycle",
        "promotion_gate": "downstream translational layer only; never use as standalone pathogenicity labels",
        "scientific_value": "drug, disease, and evidence context for translational deployment",
    },
    "clingen_erepo": {
        "training_role": "independent expert validation and adjudication",
        "refresh_cadence": "monthly frozen expert-classification snapshot",
        "promotion_gate": "external validation only unless explicitly assigned to a training release",
        "scientific_value": "FDA-recognized expert assertions with provenance for high-trust holdouts",
    },
    "cbioportal": {
        "training_role": "somatic cancer-context external validation and translational stress testing",
        "refresh_cadence": "per selected public study release or Datahub revision",
        "promotion_gate": "use as cancer-context validation, not as germline pathogenicity labels",
        "scientific_value": "independent tumor cohort evidence across BRCA, TP53, PTEN, MSH2, and KRAS",
    },
    "gdc": {
        "training_role": "TCGA/GDC open cohort validation and clinical metadata enrichment",
        "refresh_cadence": "per GDC project data release or locked project snapshot",
        "promotion_gate": "separate open and controlled-access data; never mix access tiers silently",
        "scientific_value": "large cancer-genomics cohort context with traceable project metadata",
    },
    "gwas_catalog": {
        "training_role": "gene/variant-trait association context",
        "refresh_cadence": "quarterly or before translational target-discovery analyses",
        "promotion_gate": "annotation-only; association evidence is not a clinical variant label",
        "scientific_value": "independent disease/trait association evidence for biological plausibility",
    },
    "opentargets": {
        "training_role": "target-disease and drug-discovery evidence aggregation",
        "refresh_cadence": "per Open Targets release or targeted disease-gene refresh",
        "promotion_gate": "translational prioritization only unless source-level evidence is audited",
        "scientific_value": "multi-evidence target prioritization for mechanism and therapeutic hypotheses",
    },
    "alphamissense": {
        "training_role": "independent predictor baseline and functional-prior annotation",
        "refresh_cadence": "per released score file and transcript-map lock",
        "promotion_gate": "compare against PrimeVarClass but do not use as ground truth",
        "scientific_value": "proteome-scale missense prior for comparator and disagreement discovery",
    },
    "pharmgkb": {
        "training_role": "pharmacogenomic actionability enrichment",
        "refresh_cadence": "quarterly or before drug-response/translational pilot reports",
        "promotion_gate": "pharmacogenomic evidence lane only; respect API/license terms",
        "scientific_value": "variant-drug and gene-drug evidence for translational reporting",
    },
    "lovd": {
        "training_role": "locus-specific external variant observations",
        "refresh_cadence": "manual release-frozen import after gene/database QC",
        "promotion_gate": "manual curation and schema review required before any benchmark use",
        "scientific_value": "gene-centered external evidence that can reveal cohort-specific blind spots",
    },
}

CONNECTOR_DISPLAY_NAMES = {
    "clinvar": "ClinVar",
    "mavedb": "MaveDB",
    "gnomad": "gnomAD",
    "enigma": "ENIGMA",
    "uniprot": "UniProt",
    "alphafold_db": "AlphaFold DB",
    "pdb": "RCSB PDB",
    "civic": "CIViC",
    "clingen_erepo": "ClinGen Evidence Repository",
    "cbioportal": "cBioPortal",
    "gdc": "NCI Genomic Data Commons",
    "gwas_catalog": "GWAS Catalog",
    "opentargets": "Open Targets Platform",
    "alphamissense": "AlphaMissense",
    "pharmgkb": "PharmGKB / ClinPGx",
    "lovd": "LOVD",
}


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _jsonify(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonify(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonify(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonify(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if pd.isna(value):
        return None
    return value


def _render_markdown_html(markdown_text: str, *, title: str) -> str:
    chunks: list[str] = []
    for block in str(markdown_text or "").split("\n\n"):
        stripped = block.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            chunks.append(f"<h1>{html.escape(stripped[2:])}</h1>")
            continue
        if stripped.startswith("## "):
            chunks.append(f"<h2>{html.escape(stripped[3:])}</h2>")
            continue
        if stripped.startswith("### "):
            chunks.append(f"<h3>{html.escape(stripped[4:])}</h3>")
            continue
        if stripped.startswith("- "):
            items = "".join(f"<li>{html.escape(line[2:])}</li>" for line in stripped.splitlines() if line.startswith("- "))
            chunks.append(f"<ul>{items}</ul>")
            continue
        chunks.append(f"<p>{html.escape(stripped)}</p>")
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f7f2e8;color:#17242f;max-width:1080px;margin:0 auto;padding:32px;line-height:1.65;}"
        "h1{font-size:2.2rem;}h2{margin-top:2rem;color:#2d6f73;}h3{margin-top:1.4rem;color:#20585d;}"
        "ul{background:#fff;border:1px solid #e6ddcf;border-radius:16px;padding:18px 24px;}"
        "</style></head><body>"
        + "".join(chunks)
        + "</body></html>"
    )


def _connector_catalog(bundle_items: list[dict], configured_profiles: set[str]) -> pd.DataFrame:
    bundle_index = {str(item.get("profile_id") or ""): dict(item) for item in bundle_items}
    rows: list[dict[str, Any]] = []
    for profile_id in [
        "clinvar",
        "mavedb",
        "gnomad",
        "enigma",
        "clingen_erepo",
        "uniprot",
        "alphafold_db",
        "pdb",
        "alphamissense",
        "civic",
        "cbioportal",
        "gdc",
        "gwas_catalog",
        "opentargets",
        "pharmgkb",
        "lovd",
    ]:
        recipe = dict(SYNC_RECIPES.get(profile_id) or {})
        blueprint = dict(CONNECTOR_BLUEPRINTS.get(profile_id) or {})
        bundle_item = bundle_index.get(profile_id, {})
        entrypoints = list(recipe.get("official_entrypoints") or [])
        rows.append(
            {
                "profile_id": profile_id,
                "display_name": CONNECTOR_DISPLAY_NAMES.get(profile_id, profile_id.replace("_", " ").title()),
                "in_current_config": profile_id in configured_profiles,
                "automation_level": recipe.get("automation_level", "manual_assisted"),
                "can_auto_sync_when_configured": recipe.get("automation_level") in {"automatable", "semi_automatable"},
                "bootstrap_script_ready_now": bool(bundle_item.get("can_execute_from_script")),
                "training_role": blueprint.get("training_role"),
                "refresh_cadence": blueprint.get("refresh_cadence"),
                "promotion_gate": blueprint.get("promotion_gate"),
                "scientific_value": blueprint.get("scientific_value"),
                "preferred_channel": recipe.get("preferred_channel"),
                "official_entrypoint": entrypoints[0].get("url") if entrypoints else None,
            }
        )
    return pd.DataFrame(rows)


def _automation_matrix(bundle_items: list[dict]) -> pd.DataFrame:
    if not bundle_items:
        return pd.DataFrame(
            columns=[
                "profile_id",
                "source_name",
                "automation_level",
                "can_execute_from_script",
                "local_source_exists",
                "recommended_for_live_runner",
                "next_action",
            ]
        )
    rows = []
    for item in bundle_items:
        rows.append(
            {
                "profile_id": item.get("profile_id"),
                "source_name": item.get("source_name"),
                "display_name": item.get("display_name"),
                "automation_level": item.get("automation_level"),
                "can_execute_from_script": bool(item.get("can_execute_from_script")),
                "local_source_exists": bool(item.get("local_source_exists")),
                "recommended_for_live_runner": bool(item.get("can_execute_from_script")),
                "next_action": item.get("next_action"),
                "target_dir": item.get("target_dir"),
                "release_value": item.get("release_value"),
            }
        )
    return pd.DataFrame(rows)


def _retraining_policy(configured_profiles: set[str]) -> pd.DataFrame:
    rows = [
        {
            "policy_id": "live_label_refresh",
            "sources": "ClinVar, ENIGMA",
            "active_now": bool({"clinvar", "enigma"} & configured_profiles),
            "trigger": "new review statuses, expert curation, or label shifts",
            "action": "execute sync, resolve staged config, run candidate benchmark, and compare against frozen reference",
            "promotion_gate": "promote only if locked external benchmark and calibration are preserved or improved",
        },
        {
            "policy_id": "functional_refresh",
            "sources": "MaveDB",
            "active_now": "mavedb" in configured_profiles,
            "trigger": "new score set for overlapping genes or stronger assay coverage",
            "action": "refresh functional annotations, rebuild gene-specialist candidates, and rerank mechanistic targets",
            "promotion_gate": "promote only after overlap-aware benchmark and assay-consistency checks",
        },
        {
            "policy_id": "population_refresh",
            "sources": "gnomAD",
            "active_now": "gnomad" in configured_profiles,
            "trigger": "new population release or local subset refresh",
            "action": "refresh rarity annotations and recalibrate downstream evidence layers",
            "promotion_gate": "annotation refresh can go live, but a new core model still requires a frozen benchmark rerun",
        },
        {
            "policy_id": "structure_refresh",
            "sources": "UniProt, AlphaFold DB, RCSB PDB",
            "active_now": bool({"uniprot", "alphafold_db", "pdb"} & configured_profiles),
            "trigger": "new accession mapping, structural model, or experimental structure",
            "action": "refresh protein-impact and quantum prioritization without changing core labels",
            "promotion_gate": "structural evidence strengthens interpretation; it should not alone trigger model promotion",
        },
        {
            "policy_id": "translational_refresh",
            "sources": "CIViC, cBioPortal, GDC, Open Targets, PharmGKB",
            "active_now": bool({"civic", "cbioportal", "gdc", "opentargets", "pharmgkb"} & configured_profiles),
            "trigger": "new disease, drug, or actionability evidence",
            "action": "refresh translational ranking, pilot prioritization, and reporting layers",
            "promotion_gate": "never use as standalone supervision for pathogenicity classification",
        },
        {
            "policy_id": "independent_expert_refresh",
            "sources": "ClinGen ERepo, LOVD",
            "active_now": bool({"clingen_erepo", "lovd"} & configured_profiles),
            "trigger": "new expert classification, locus-specific variant observations, or resolved classification conflict",
            "action": "stage as independent validation/adjudication evidence and rerun leakage checks",
            "promotion_gate": "promote only after frozen split review confirms independence from training labels",
        },
        {
            "policy_id": "external_predictor_refresh",
            "sources": "AlphaMissense, GWAS Catalog, Open Targets",
            "active_now": bool({"alphamissense", "gwas_catalog", "opentargets"} & configured_profiles),
            "trigger": "new predictor scores, association releases, or target-disease evidence updates",
            "action": "refresh comparator/evidence layers and prioritize disagreement-driven discovery",
            "promotion_gate": "never replace independent labels with predictor-derived pseudo-labels",
        },
    ]
    return pd.DataFrame(rows)


def _governance_lanes() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "lane": "live_learning_lane",
                "purpose": "keep public evidence current and retrain candidate models",
                "data_behavior": "ingest freshest staged public sources and allow frequent candidate refreshes",
                "claim_policy": "no definitive scientific or therapeutic claims from this lane alone",
                "promotion_gate": "must beat or match the frozen release on locked benchmarks",
            },
            {
                "lane": "frozen_release_lane",
                "purpose": "support manuscripts, validation packages, and external comparison",
                "data_behavior": "use release-frozen artifacts, hashes, manifests, and locked cohort definitions",
                "claim_policy": "all major claims and comparisons should point to this lane",
                "promotion_gate": "immutable until a new versioned release is deliberately created",
            },
        ]
    )


def _runner_script(
    *,
    source_root: Path,
    config_path: str,
    bootstrap_output_dir: Path,
    resolution_output_dir: Path,
    training_output_dir: Path,
    ingest_output_dir: Path,
    last_run_path: Path,
    mode: str,
    high_confidence_only: bool,
    model_families: list[str] | None,
    selected_sources: list[str],
) -> str:
    return f"""from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, {json.dumps(str(source_root))})

from primevarclass import (
    execute_public_source_bootstrap_bundle,
    export_public_source_resolution,
    ingest_sources_from_config,
    train_from_source_config,
)


CONFIG_PATH = {json.dumps(str(Path(config_path).resolve()))}
BOOTSTRAP_OUTPUT_DIR = {json.dumps(str(bootstrap_output_dir))}
RESOLUTION_OUTPUT_DIR = {json.dumps(str(resolution_output_dir))}
TRAINING_OUTPUT_DIR = {json.dumps(str(training_output_dir))}
INGEST_OUTPUT_DIR = {json.dumps(str(ingest_output_dir))}
LAST_RUN_PATH = {json.dumps(str(last_run_path))}
MODE = {json.dumps(str(mode))}
HIGH_CONFIDENCE_ONLY = {json.dumps(bool(high_confidence_only))}
MODEL_FAMILIES = {json.dumps(model_families or [])}
SELECTED_SOURCES = {json.dumps(selected_sources)}


def main() -> None:
    Path(LAST_RUN_PATH).parent.mkdir(parents=True, exist_ok=True)
    ingestion = ingest_sources_from_config(CONFIG_PATH, output_dir=INGEST_OUTPUT_DIR)
    assessment = ingestion.get("public_source_assessment") or {{}}
    sync_plan = ingestion.get("public_source_sync_plan") or {{}}

    execution = {{}}
    resolved_config_path = CONFIG_PATH
    if SELECTED_SOURCES:
        execution = execute_public_source_bootstrap_bundle(
            config_path=CONFIG_PATH,
            public_source_assessment=assessment,
            public_source_sync_plan=sync_plan,
            output_dir=BOOTSTRAP_OUTPUT_DIR,
            dry_run=False,
            selected_sources=SELECTED_SOURCES,
        )
        try:
            resolution = export_public_source_resolution(
                config_path=CONFIG_PATH,
                bootstrap_output_dir=BOOTSTRAP_OUTPUT_DIR,
                output_dir=RESOLUTION_OUTPUT_DIR,
            )
            resolved_config_path = resolution.get("resolved_config_path") or CONFIG_PATH
        except Exception as exc:  # pragma: no cover
            execution["resolution_warning"] = str(exc)

    training = train_from_source_config(
        config_path=resolved_config_path,
        output_dir=TRAINING_OUTPUT_DIR,
        mode=MODE,
        keep_metadata=True,
        high_confidence_only=HIGH_CONFIDENCE_ONLY,
        model_families=MODEL_FAMILIES or None,
    )

    payload = {{
        "config_path": CONFIG_PATH,
        "resolved_config_path": resolved_config_path,
        "selected_sources": SELECTED_SOURCES,
        "execution_summary": execution.get("summary") or {{}},
        "training_summary_path": training.get("summary_report_path"),
        "training_metrics_path": training.get("export_paths", {{}}).get("metrics"),
        "catalog_readiness_percent": (assessment.get("summary") or {{}}).get("overall_readiness_percent"),
        "sync_candidates": (sync_plan.get("summary") or {{}}).get("n_sync_candidates"),
    }}
    Path(LAST_RUN_PATH).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
"""


def _build_markdown(
    *,
    summary: dict,
    connector_catalog: pd.DataFrame,
    automation_matrix: pd.DataFrame,
    retraining_policy: pd.DataFrame,
    governance_lanes: pd.DataFrame,
    benchmark_readiness: dict,
) -> str:
    lines = [
        "# PrimeVarClass Continuous Learning",
        "",
        f"- Generated at: {summary.get('generated_at')}",
        f"- Configured public sources: {summary.get('configured_public_source_count')}",
        f"- Auto-sync coverage: {summary.get('auto_sync_coverage_percent')}%",
        f"- Script-execution coverage: {summary.get('script_execution_coverage_percent')}%",
        f"- Continuous-learning readiness: {summary.get('continuous_learning_readiness_percent')}%",
        f"- Benchmark readiness: {(benchmark_readiness.get('summary') or {}).get('benchmark_readiness_percent', 0)}%",
        f"- Live runner selected sources: {', '.join(summary.get('live_runner_selected_sources') or []) or '-'}",
        "",
        "## Why This Matters",
        "",
        "- The platform can now maintain a live-learning lane that syncs supported public sources, resolves staged artifacts into a runnable config, and retrains candidate models automatically.",
        "- At the same time, the platform preserves a frozen-release lane so scientific validation, manuscripts, and high-stakes comparisons stay reproducible.",
        "",
        "## Configured Connectors",
        "",
    ]
    configured = connector_catalog[connector_catalog["in_current_config"] == True].copy() if not connector_catalog.empty else pd.DataFrame()
    for _, row in configured.iterrows():
        lines.extend(
            [
                f"### {row.get('display_name')}",
                "",
                f"- Automation level: {row.get('automation_level')}",
                f"- Bootstrap ready now: {'yes' if bool(row.get('bootstrap_script_ready_now')) else 'no'}",
                f"- Training role: {row.get('training_role')}",
                f"- Scientific value: {row.get('scientific_value')}",
                f"- Promotion gate: {row.get('promotion_gate')}",
                "",
            ]
        )
    lines.extend(["## Expansion Connectors", ""])
    expansion = connector_catalog[connector_catalog["in_current_config"] == False].copy() if not connector_catalog.empty else pd.DataFrame()
    for _, row in expansion.iterrows():
        lines.append(
            f"- {row.get('display_name')}: {row.get('scientific_value')} "
            f"(cadence: {row.get('refresh_cadence')}; gate: {row.get('promotion_gate')})"
        )
    lines.extend(["", "## Retraining Policy", ""])
    for _, row in retraining_policy.iterrows():
        lines.extend(
            [
                f"### {row.get('policy_id')}",
                "",
                f"- Sources: {row.get('sources')}",
                f"- Active now: {'yes' if bool(row.get('active_now')) else 'no'}",
                f"- Trigger: {row.get('trigger')}",
                f"- Action: {row.get('action')}",
                f"- Promotion gate: {row.get('promotion_gate')}",
                "",
            ]
        )
    lines.extend(["## Governance Lanes", ""])
    for _, row in governance_lanes.iterrows():
        lines.extend(
            [
                f"### {row.get('lane')}",
                "",
                f"- Purpose: {row.get('purpose')}",
                f"- Data behavior: {row.get('data_behavior')}",
                f"- Claim policy: {row.get('claim_policy')}",
                f"- Promotion gate: {row.get('promotion_gate')}",
                "",
            ]
        )
    if not automation_matrix.empty:
        lines.extend(["## Automation Matrix", ""])
        for _, row in automation_matrix.iterrows():
            lines.append(
                f"- {row.get('source_name')} ({row.get('profile_id')}): "
                f"automation={row.get('automation_level')}, "
                f"script_ready={'yes' if bool(row.get('can_execute_from_script')) else 'no'}, "
                f"next={row.get('next_action')}"
            )
    return "\n".join(lines).strip()


def build_continuous_learning_package(
    *,
    config_path: str,
    output_dir: str,
    mode: str = "hybrid",
    high_confidence_only: bool = False,
    model_families: list[str] | None = None,
) -> dict[str, Any]:
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    catalog_snapshot_dir = output_root / "catalog_snapshot"
    bootstrap_output_dir = output_root / "bootstrap_workspace"
    resolution_output_dir = output_root / "resolution_workspace"
    training_output_dir = output_root / "training_workspace"
    last_run_path = output_root / "continuous_learning_last_run.json"

    ingestion = ingest_sources_from_config(config_path=config_path, output_dir=str(catalog_snapshot_dir))
    assessment = ingestion.get("public_source_assessment") or {}
    sync_plan = ingestion.get("public_source_sync_plan") or {}
    bootstrap_bundle = build_public_source_bootstrap_bundle(
        config_path=config_path,
        public_source_assessment=assessment,
        public_source_sync_plan=sync_plan,
        output_dir=str(bootstrap_output_dir),
    )
    sync_history = load_public_source_sync_history(
        output_dir=str(bootstrap_output_dir),
        public_source_assessment=assessment,
        public_source_sync_plan=sync_plan,
    )
    benchmark_readiness = build_public_benchmark_readiness(
        public_source_assessment=assessment,
        public_source_sync_plan=sync_plan,
        sync_history=sync_history,
        bootstrap_bundle=bootstrap_bundle,
    )

    configured_profiles = {
        str(item.get("profile_id") or "")
        for item in (assessment.get("sources") or [])
        if item.get("recognized_public_source")
    }
    connector_catalog = _connector_catalog(list(bootstrap_bundle.get("bundle_items") or []), configured_profiles)
    automation_matrix = _automation_matrix(list(bootstrap_bundle.get("bundle_items") or []))
    retraining_policy = _retraining_policy(configured_profiles)
    governance_lanes = _governance_lanes()
    selected_sources = [
        str(item.get("source_name"))
        for item in (bootstrap_bundle.get("bundle_items") or [])
        if item.get("can_execute_from_script")
    ]

    configured_count = int(len(configured_profiles))
    auto_sync_count = int(sum(1 for item in (sync_plan.get("sync_items") or []) if item.get("can_auto_sync")))
    script_ready_count = int(sum(1 for item in (bootstrap_bundle.get("bundle_items") or []) if item.get("can_execute_from_script")))
    auto_sync_coverage = int(round((auto_sync_count / configured_count) * 100)) if configured_count else 0
    script_coverage = int(round((script_ready_count / configured_count) * 100)) if configured_count else 0
    benchmark_percent = int((benchmark_readiness.get("summary") or {}).get("benchmark_readiness_percent") or 0)
    continuous_percent = int(round((0.35 * auto_sync_coverage) + (0.30 * script_coverage) + (0.35 * benchmark_percent))) if configured_count else 0

    summary = {
        "generated_at": _now_utc(),
        "config_path": str(Path(config_path).resolve()),
        "configured_public_source_count": configured_count,
        "auto_sync_source_count": auto_sync_count,
        "script_ready_source_count": script_ready_count,
        "auto_sync_coverage_percent": auto_sync_coverage,
        "script_execution_coverage_percent": script_coverage,
        "continuous_learning_readiness_percent": continuous_percent,
        "recommended_expansion_connector_count": int(len(connector_catalog.loc[connector_catalog["in_current_config"] == False])),
        "live_runner_selected_sources": selected_sources,
        "catalog_snapshot_dir": str(catalog_snapshot_dir),
        "bootstrap_output_dir": str(bootstrap_output_dir),
        "resolution_output_dir": str(resolution_output_dir),
        "training_output_dir": str(training_output_dir),
        "last_run_path": str(last_run_path),
    }
    markdown_report = _build_markdown(
        summary=summary,
        connector_catalog=connector_catalog,
        automation_matrix=automation_matrix,
        retraining_policy=retraining_policy,
        governance_lanes=governance_lanes,
        benchmark_readiness=benchmark_readiness,
    )
    runner_script = _runner_script(
        source_root=Path(__file__).resolve().parents[1],
        config_path=config_path,
        bootstrap_output_dir=bootstrap_output_dir,
        resolution_output_dir=resolution_output_dir,
        training_output_dir=training_output_dir,
        ingest_output_dir=catalog_snapshot_dir,
        last_run_path=last_run_path,
        mode=mode,
        high_confidence_only=high_confidence_only,
        model_families=model_families,
        selected_sources=selected_sources,
    )
    return {
        "summary": summary,
        "public_source_assessment": assessment,
        "public_source_sync_plan": sync_plan,
        "bootstrap_bundle": bootstrap_bundle,
        "sync_history": sync_history,
        "benchmark_readiness": benchmark_readiness,
        "connector_catalog": connector_catalog,
        "automation_matrix": automation_matrix,
        "retraining_policy": retraining_policy,
        "governance_lanes": governance_lanes,
        "markdown_report": markdown_report,
        "html_report": _render_markdown_html(markdown_report, title="PrimeVarClass Continuous Learning"),
        "runner_script": runner_script,
    }


def export_continuous_learning_package(
    *,
    config_path: str,
    output_dir: str = "primevarclass_continuous_learning_results",
    mode: str = "hybrid",
    high_confidence_only: bool = False,
    model_families: list[str] | None = None,
) -> dict[str, Any]:
    bundle = build_continuous_learning_package(
        config_path=config_path,
        output_dir=output_dir,
        mode=mode,
        high_confidence_only=high_confidence_only,
        model_families=model_families,
    )
    output_root = Path(output_dir).resolve()
    manifest_path = output_root / "continuous_learning_manifest.json"
    markdown_path = output_root / "continuous_learning_report.md"
    html_path = output_root / "continuous_learning_report.html"
    connector_catalog_path = output_root / "continuous_learning_connector_catalog.csv"
    automation_matrix_path = output_root / "continuous_learning_automation_matrix.csv"
    retraining_policy_path = output_root / "continuous_learning_retraining_policy.csv"
    governance_lanes_path = output_root / "continuous_learning_governance_lanes.csv"
    runner_script_path = output_root / "continuous_learning_runner.py"

    markdown_path.write_text(str(bundle.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(str(bundle.get("html_report") or ""), encoding="utf-8")
    bundle["connector_catalog"].to_csv(connector_catalog_path, index=False)
    bundle["automation_matrix"].to_csv(automation_matrix_path, index=False)
    bundle["retraining_policy"].to_csv(retraining_policy_path, index=False)
    bundle["governance_lanes"].to_csv(governance_lanes_path, index=False)
    runner_script_path.write_text(str(bundle.get("runner_script") or ""), encoding="utf-8")

    manifest = {
        "summary": _jsonify(bundle.get("summary") or {}),
        "benchmark_readiness": _jsonify(bundle.get("benchmark_readiness") or {}),
        "public_source_assessment": _jsonify(bundle.get("public_source_assessment") or {}),
        "public_source_sync_plan": _jsonify(bundle.get("public_source_sync_plan") or {}),
        "bootstrap_bundle_manifest_path": (bundle.get("bootstrap_bundle") or {}).get("manifest_path"),
        "sync_history_summary": _jsonify((bundle.get("sync_history") or {}).get("summary") or {}),
        "artifacts": {
            "continuous_learning_report_markdown_path": str(markdown_path),
            "continuous_learning_report_html_path": str(html_path),
            "continuous_learning_connector_catalog_path": str(connector_catalog_path),
            "continuous_learning_automation_matrix_path": str(automation_matrix_path),
            "continuous_learning_retraining_policy_path": str(retraining_policy_path),
            "continuous_learning_governance_lanes_path": str(governance_lanes_path),
            "continuous_learning_runner_path": str(runner_script_path),
        },
    }
    manifest_path.write_text(json.dumps(_jsonify(manifest), indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "continuous_learning_manifest_path": str(manifest_path),
        "continuous_learning_report_markdown_path": str(markdown_path),
        "continuous_learning_report_html_path": str(html_path),
        "continuous_learning_connector_catalog_path": str(connector_catalog_path),
        "continuous_learning_automation_matrix_path": str(automation_matrix_path),
        "continuous_learning_retraining_policy_path": str(retraining_policy_path),
        "continuous_learning_governance_lanes_path": str(governance_lanes_path),
        "continuous_learning_runner_path": str(runner_script_path),
        "summary": bundle.get("summary") or {},
        "benchmark_readiness": bundle.get("benchmark_readiness") or {},
        "bootstrap_bundle": bundle.get("bootstrap_bundle") or {},
    }
