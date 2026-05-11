from __future__ import annotations

import importlib.util
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .real_data_preparation import _jsonify, _render_markdown_html


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        numeric = float(value)
    except Exception:
        return default
    if np.isnan(numeric) or np.isinf(numeric):
        return default
    return numeric


def _load_manifest(path_value: str) -> dict[str, Any]:
    path = Path(path_value).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path_value}")
    return json.loads(path.read_text(encoding="utf-8"))


def _read_table(path_value: Any) -> pd.DataFrame:
    if not path_value:
        return pd.DataFrame()
    path = Path(str(path_value)).expanduser()
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def _engine_status() -> dict[str, bool]:
    return {
        "xtb": bool(shutil.which("xtb")),
        "psi4": bool(shutil.which("psi4")),
        "vina": bool(shutil.which("vina") or shutil.which("autodock_vina")),
        "openmm": importlib.util.find_spec("openmm") is not None,
        "qiskit_nature": importlib.util.find_spec("qiskit_nature") is not None,
    }


def _template_path(root: Path, model_request_id: str, suffix: str) -> str | None:
    if not model_request_id:
        return None
    candidate = root / f"{model_request_id}{suffix}"
    return str(candidate) if candidate.exists() else None


def _vulnerability_bonus(value: Any) -> float:
    token = str(value or "").strip().lower()
    if "metal" in token or "cysteine" in token:
        return 10.0
    if "catalytic" in token or "nucleotide" in token:
        return 8.0
    if "interface" in token or "binding" in token:
        return 6.0
    return 4.0


def _campaign_row(row: pd.Series, engine_state: dict[str, bool], quantum_root: Path, vqe_root: Path) -> dict[str, Any]:
    protein_impact = _safe_float(row.get("protein_impact_score_percent"))
    prime_mechanistic = _safe_float(row.get("prime_mechanistic_score_percent"))
    quantum_priority = _safe_float(row.get("quantum_priority_score_percent"))
    coupling = _safe_float(row.get("prime_quantum_coupling_score_percent"))
    charge_abs_diff = abs(_safe_float(row.get("charge_abs_diff")))
    hydro_abs_diff = abs(_safe_float(row.get("hydro_abs_diff")))
    vulnerability_bonus = _vulnerability_bonus(row.get("quantum_vulnerability_class"))

    surrogate_structural_signal = np.clip(
        (0.40 * protein_impact)
        + (0.25 * prime_mechanistic)
        + (0.20 * quantum_priority)
        + (0.15 * coupling)
        + vulnerability_bonus,
        0.0,
        100.0,
    )
    mutant_reference_delta_proxy = np.clip(
        (0.45 * prime_mechanistic)
        + (0.25 * protein_impact)
        + (0.12 * quantum_priority)
        + (0.08 * min(charge_abs_diff * 20.0, 20.0))
        + (0.10 * min(hydro_abs_diff * 4.0, 20.0)),
        0.0,
        100.0,
    )
    structural_alignment = np.clip(
        np.mean([prime_mechanistic, coupling, surrogate_structural_signal]),
        0.0,
        100.0,
    )

    model_request_id = str(row.get("model_request_id") or "")
    xtb_template_path = _template_path(quantum_root, model_request_id, ".xtb.sh")
    psi4_template_path = _template_path(quantum_root, model_request_id, ".psi4.in")
    openmm_template_path = _template_path(quantum_root, model_request_id, ".openmm_plan.py")
    vina_template_path = _template_path(quantum_root, model_request_id, ".vina_config.txt")
    qiskit_template_path = _template_path(vqe_root, model_request_id, ".qiskit_nature_vqe.py")

    template_ready = any([xtb_template_path, psi4_template_path, openmm_template_path, vina_template_path, qiskit_template_path])
    xtb_ready = bool(template_ready and xtb_template_path and engine_state["xtb"])
    dft_ready = bool(template_ready and psi4_template_path and engine_state["psi4"])
    if xtb_ready and dft_ready:
        campaign_status = "execution_ready"
    elif template_ready:
        campaign_status = "template_ready_engines_missing"
    else:
        campaign_status = "prioritized_requires_template_refresh"

    drug_discovery_readiness = np.clip(
        (0.55 * surrogate_structural_signal)
        + (0.20 * structural_alignment)
        + (15.0 if vina_template_path else 0.0)
        + (10.0 if qiskit_template_path else 0.0),
        0.0,
        100.0,
    )

    return {
        "gene": row.get("gene"),
        "hgvs_p": row.get("hgvs_p"),
        "model_request_id": model_request_id,
        "protein_impact_score_percent": round(protein_impact, 1),
        "prime_mechanistic_score_percent": round(prime_mechanistic, 1),
        "quantum_priority_score_percent": round(quantum_priority, 1),
        "prime_quantum_coupling_score_percent": round(coupling, 1),
        "structural_region": row.get("structural_region"),
        "domain_mechanism": row.get("domain_mechanism"),
        "quantum_vulnerability_class": row.get("quantum_vulnerability_class"),
        "mechanism_tags": row.get("mechanism_tags"),
        "recommended_quantum_methods": row.get("recommended_quantum_methods"),
        "recommended_assays": row.get("recommended_assays"),
        "drug_discovery_angle": row.get("drug_discovery_angle"),
        "surrogate_structural_signal_percent": round(float(surrogate_structural_signal), 1),
        "mutant_reference_delta_proxy_percent": round(float(mutant_reference_delta_proxy), 1),
        "prime_quantum_structural_alignment_percent": round(float(structural_alignment), 1),
        "drug_discovery_readiness_percent": round(float(drug_discovery_readiness), 1),
        "xtb_template_path": xtb_template_path,
        "psi4_template_path": psi4_template_path,
        "openmm_template_path": openmm_template_path,
        "vina_template_path": vina_template_path,
        "qiskit_nature_vqe_template_path": qiskit_template_path,
        "xtb_engine_available": bool(engine_state["xtb"]),
        "psi4_engine_available": bool(engine_state["psi4"]),
        "openmm_engine_available": bool(engine_state["openmm"]),
        "vina_engine_available": bool(engine_state["vina"]),
        "xtb_execution_ready": xtb_ready,
        "dft_execution_ready": dft_ready,
        "campaign_status": campaign_status,
    }


def _build_campaign_table(
    protein_queue: pd.DataFrame,
    quantum_targets: pd.DataFrame,
    vqe_targets: pd.DataFrame,
    engine_state: dict[str, bool],
    quantum_root: Path,
    vqe_root: Path,
    max_targets: int,
) -> pd.DataFrame:
    protein = protein_queue.copy()
    if protein.empty:
        return pd.DataFrame()
    protein["gene"] = protein["gene"].astype(str).str.upper()
    protein = protein.loc[protein["gene"] == "BRCA1"].copy()
    if protein.empty:
        return pd.DataFrame()
    quantum = quantum_targets.copy()
    if not quantum.empty:
        quantum["gene"] = quantum["gene"].astype(str).str.upper()
    vqe = vqe_targets.copy()
    if not vqe.empty:
        vqe["gene"] = vqe["gene"].astype(str).str.upper()

    merged = protein.merge(
        quantum[
            [
                "gene",
                "hgvs_p",
                "model_request_id",
                "quantum_priority_score_percent",
                "prime_quantum_coupling_score_percent",
                "quantum_vulnerability_class",
                "recommended_quantum_methods",
                "drug_discovery_angle",
            ]
        ] if not quantum.empty else pd.DataFrame(columns=["gene", "hgvs_p", "model_request_id"]),
        on=["gene", "hgvs_p", "model_request_id"],
        how="left",
    )
    merged = merged.merge(
        vqe[["gene", "hgvs_p", "model_request_id"]] if not vqe.empty else pd.DataFrame(columns=["gene", "hgvs_p", "model_request_id"]),
        on=["gene", "hgvs_p", "model_request_id"],
        how="left",
        suffixes=("", "__vqe"),
    )
    merged = merged.sort_values(
        ["protein_impact_score_percent", "prime_mechanistic_score_percent", "queue_rank"],
        ascending=[False, False, True],
        kind="stable",
    ).head(max_targets)
    rows = [_campaign_row(row, engine_state, quantum_root, vqe_root) for _, row in merged.iterrows()]
    return pd.DataFrame(rows)


def _build_markdown(bundle: dict[str, Any]) -> str:
    summary = dict(bundle.get("summary") or {})
    campaign = bundle.get("campaign_table")
    campaign_df = campaign if isinstance(campaign, pd.DataFrame) else pd.DataFrame()
    engine_state = dict(bundle.get("engine_state") or {})
    blockers = [name for name, available in engine_state.items() if not available]
    lines = [
        "# PrimeVarClass BRCA1 Structural Campaign",
        "",
        f"- Generated at: `{summary.get('generated_at')}`",
        f"- BRCA1 campaign targets: `{summary.get('campaign_target_count', 0)}`",
        f"- Template coverage: `{summary.get('template_coverage_percent', 0)}%`",
        f"- Campaign readiness: `{summary.get('campaign_readiness_percent', 0)}%`",
        f"- Mean structural signal: `{summary.get('mean_surrogate_structural_signal_percent', 0.0)}%`",
        f"- Mean drug-discovery readiness: `{summary.get('mean_drug_discovery_readiness_percent', 0.0)}%`",
        f"- xTB-ready targets: `{summary.get('xtb_execution_ready_count', 0)}`",
        f"- DFT-ready targets: `{summary.get('dft_execution_ready_count', 0)}`",
        "",
        "## Engine preflight",
        "",
        f"- xTB available: `{'yes' if engine_state.get('xtb') else 'no'}`",
        f"- Psi4 available: `{'yes' if engine_state.get('psi4') else 'no'}`",
        f"- OpenMM available: `{'yes' if engine_state.get('openmm') else 'no'}`",
        f"- AutoDock Vina available: `{'yes' if engine_state.get('vina') else 'no'}`",
        f"- Missing blockers: `{', '.join(blockers) if blockers else 'none'}`",
        "",
        "## Top BRCA1 targets",
        "",
    ]
    if campaign_df.empty:
        lines.append("- No BRCA1 structural campaign targets were available.")
    else:
        for row in campaign_df.head(10).to_dict(orient="records"):
            lines.append(
                "- "
                f"{row.get('gene')} {row.get('hgvs_p')}: "
                f"signal={row.get('surrogate_structural_signal_percent')}%, "
                f"delta={row.get('mutant_reference_delta_proxy_percent')}%, "
                f"alignment={row.get('prime_quantum_structural_alignment_percent')}%, "
                f"status={row.get('campaign_status')}"
            )
    lines.extend(
        [
            "",
            "## Guardrail",
            "",
            "- This package organizes a BRCA1 execution campaign with honest preflight status.",
            "- If xTB or Psi4 are missing, the current outputs remain surrogate prioritization plus ready-to-run templates.",
            "- Do not claim executed QM/DFT evidence until the engine status is green and coordinates are reviewed.",
        ]
    )
    return "\n".join(lines).strip()


def build_brca1_structural_campaign(
    *,
    protein_impact_manifest_path: str,
    quantum_proteomics_manifest_path: str,
    max_targets: int = 12,
) -> dict[str, Any]:
    protein_manifest = _load_manifest(protein_impact_manifest_path)
    quantum_manifest = _load_manifest(quantum_proteomics_manifest_path)
    protein_queue = _read_table(protein_manifest.get("modeling_queue_path"))
    quantum_targets = _read_table(quantum_manifest.get("quantum_targets_path"))
    vqe_targets = _read_table(quantum_manifest.get("vqe_targets_path"))
    quantum_root = Path(quantum_proteomics_manifest_path).expanduser().resolve().parent / "quantum_job_templates"
    vqe_root = Path(quantum_proteomics_manifest_path).expanduser().resolve().parent / "vqe_job_templates"
    engine_state = _engine_status()
    campaign_table = _build_campaign_table(
        protein_queue=protein_queue,
        quantum_targets=quantum_targets,
        vqe_targets=vqe_targets,
        engine_state=engine_state,
        quantum_root=quantum_root,
        vqe_root=vqe_root,
        max_targets=max_targets,
    )

    template_coverage = int(round(float(campaign_table["xtb_template_path"].notna().mean()) * 100.0)) if not campaign_table.empty else 0
    template_any_coverage = int(
        round(
            float(
                campaign_table[
                    [
                        "xtb_template_path",
                        "psi4_template_path",
                        "openmm_template_path",
                        "vina_template_path",
                        "qiskit_nature_vqe_template_path",
                    ]
                ].notna().any(axis=1).mean()
            )
            * 100.0
        )
    ) if not campaign_table.empty else 0
    engine_availability_percent = int(round((sum(1 for value in engine_state.values() if value) / max(len(engine_state), 1)) * 100.0))
    mean_signal = round(float(campaign_table["surrogate_structural_signal_percent"].mean()), 1) if not campaign_table.empty else 0.0
    mean_drug_readiness = round(float(campaign_table["drug_discovery_readiness_percent"].mean()), 1) if not campaign_table.empty else 0.0
    campaign_readiness = int(
        round(
            (0.45 * template_any_coverage)
            + (0.25 * engine_availability_percent)
            + (0.30 * mean_signal)
        )
    )
    summary = {
        "generated_at": _now_utc(),
        "campaign_target_count": int(len(campaign_table)),
        "template_coverage_percent": template_any_coverage,
        "campaign_readiness_percent": campaign_readiness,
        "mean_surrogate_structural_signal_percent": mean_signal,
        "mean_mutant_reference_delta_proxy_percent": round(float(campaign_table["mutant_reference_delta_proxy_percent"].mean()), 1) if not campaign_table.empty else 0.0,
        "mean_prime_quantum_structural_alignment_percent": round(float(campaign_table["prime_quantum_structural_alignment_percent"].mean()), 1) if not campaign_table.empty else 0.0,
        "mean_drug_discovery_readiness_percent": mean_drug_readiness,
        "xtb_execution_ready_count": int(campaign_table["xtb_execution_ready"].sum()) if not campaign_table.empty else 0,
        "dft_execution_ready_count": int(campaign_table["dft_execution_ready"].sum()) if not campaign_table.empty else 0,
        "top_targets": (
            (campaign_table["gene"].astype(str) + " " + campaign_table["hgvs_p"].astype(str)).head(8).tolist()
            if not campaign_table.empty
            else []
        ),
        "source_protein_impact_manifest_path": str(Path(protein_impact_manifest_path).expanduser().resolve()),
        "source_quantum_proteomics_manifest_path": str(Path(quantum_proteomics_manifest_path).expanduser().resolve()),
    }
    bundle = {
        "summary": summary,
        "campaign_table": campaign_table,
        "engine_state": engine_state,
    }
    bundle["markdown_report"] = _build_markdown(bundle)
    bundle["html_report"] = _render_markdown_html(bundle["markdown_report"], "PrimeVarClass BRCA1 Structural Campaign")
    return bundle


def export_brca1_structural_campaign(
    *,
    protein_impact_manifest_path: str,
    quantum_proteomics_manifest_path: str,
    output_dir: str,
    max_targets: int = 12,
) -> dict[str, Any]:
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    bundle = build_brca1_structural_campaign(
        protein_impact_manifest_path=protein_impact_manifest_path,
        quantum_proteomics_manifest_path=quantum_proteomics_manifest_path,
        max_targets=max_targets,
    )

    campaign_path = output_root / "brca1_structural_campaign.csv"
    markdown_path = output_root / "brca1_structural_campaign_report.md"
    html_path = output_root / "brca1_structural_campaign_report.html"
    manifest_path = output_root / "brca1_structural_campaign_manifest.json"

    campaign_df = bundle.get("campaign_table")
    (campaign_df if isinstance(campaign_df, pd.DataFrame) else pd.DataFrame()).to_csv(campaign_path, index=False)
    markdown_path.write_text(str(bundle.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(str(bundle.get("html_report") or ""), encoding="utf-8")

    manifest_payload = {
        "generated_at": _now_utc(),
        "summary": bundle.get("summary") or {},
        "engine_state": bundle.get("engine_state") or {},
        "campaign_path": str(campaign_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
    }
    manifest_path.write_text(json.dumps(_jsonify(manifest_payload), indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "brca1_structural_campaign": bundle,
        "brca1_structural_campaign_manifest_path": str(manifest_path),
        "brca1_structural_campaign_path": str(campaign_path),
        "brca1_structural_campaign_report_markdown_path": str(markdown_path),
        "brca1_structural_campaign_report_html_path": str(html_path),
    }
