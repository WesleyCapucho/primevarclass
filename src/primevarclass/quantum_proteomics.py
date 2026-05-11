from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .core import next_prime
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


def _load_manifest(path: str) -> dict[str, Any]:
    candidate = Path(path).expanduser()
    if not candidate.exists():
        raise FileNotFoundError(f"Protein-impact manifest not found: {path}")
    return json.loads(candidate.read_text(encoding="utf-8"))


def _read_table(path_value: Any) -> pd.DataFrame:
    if not path_value:
        return pd.DataFrame()
    path = Path(str(path_value)).expanduser()
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, sep=None, engine="python")
    except Exception:
        return pd.DataFrame()


def _tag_tokens(row: pd.Series) -> set[str]:
    values = [
        str(row.get("mechanism_tags") or ""),
        str(row.get("domain_mechanism") or ""),
        str(row.get("structural_region") or ""),
    ]
    tokens: set[str] = set()
    for value in values:
        normalized = value.replace(",", ";").replace("|", ";").replace(" ", "_")
        tokens.update(token.strip().lower() for token in normalized.split(";") if token.strip())
    return tokens


def _vulnerability_class(row: pd.Series) -> str:
    tokens = _tag_tokens(row)
    if any("cysteine" in token or "zinc" in token or "metal" in token or "redox" in token for token in tokens):
        return "metal_redox_or_cysteine_network"
    if any("catalysis" in token or "atpase" in token or "gtpase" in token or "nucleotide" in token for token in tokens):
        return "catalytic_or_nucleotide_site"
    if any("binding" in token or "interface" in token or "rad51" in token or "partner" in token for token in tokens):
        return "protein_or_ligand_interface"
    if any("dna" in token or "electrostatic" in token for token in tokens):
        return "electrostatic_or_dna_binding_surface"
    if any("hydrophobic" in token or "fold" in token or "packing" in token for token in tokens):
        return "folding_stability_or_hydrophobic_core"
    return "context_dependent_quantum_site"


def _recommended_quantum_methods(row: pd.Series) -> list[str]:
    vulnerability = _vulnerability_class(row)
    methods = ["xTB_GFN2_screen"]
    if vulnerability in {"metal_redox_or_cysteine_network", "catalytic_or_nucleotide_site"}:
        methods.extend(["DFT_fragment_single_point", "QM_MM_boundary_refinement"])
    if vulnerability in {"protein_or_ligand_interface", "electrostatic_or_dna_binding_surface"}:
        methods.extend(["QM_charge_model", "OpenMM_local_MD"])
    if vulnerability == "folding_stability_or_hydrophobic_core":
        methods.extend(["OpenMM_local_MD", "mutant_vs_reference_contact_scan"])
    methods.append("docking_hotspot_screen")
    return list(dict.fromkeys(methods))


def _drug_discovery_angle(row: pd.Series) -> str:
    vulnerability = _vulnerability_class(row)
    if vulnerability == "metal_redox_or_cysteine_network":
        return "Test whether mutation perturbs metal/redox coordination; prioritize stabilizers or interface-rescue hypotheses only after structural validation."
    if vulnerability == "catalytic_or_nucleotide_site":
        return "Evaluate nucleotide/catalytic microenvironment and ligandability; prioritize allosteric or catalytic-state modulators after assay confirmation."
    if vulnerability == "protein_or_ligand_interface":
        return "Map interface disruption and search for pockets or molecular glues that could stabilize the relevant interaction."
    if vulnerability == "electrostatic_or_dna_binding_surface":
        return "Quantify local charge redistribution and test whether DNA/interface recognition can be rescued or selectively disrupted."
    if vulnerability == "folding_stability_or_hydrophobic_core":
        return "Quantify destabilization and prioritize chaperone-like stabilizer or conformation-rescue hypotheses."
    return "Use QM/MD to determine whether the site exposes a tractable pocket, altered charge network, or mutant-specific interaction surface."


def _score_quantum_priority(row: pd.Series) -> float:
    impact = _safe_float(row.get("protein_impact_score_percent")) / 100.0
    prime = _safe_float(row.get("prime_mechanistic_score_percent")) / 100.0
    biochemical = min(_safe_float(row.get("biochemical_severity")) / 12.0, 1.0)
    charge = min(abs(_safe_float(row.get("charge_abs_diff"))) / 2.0, 1.0)
    hydro = min(abs(_safe_float(row.get("hydro_abs_diff"))) / 5.0, 1.0)
    vulnerability_bonus = 0.0
    vulnerability = _vulnerability_class(row)
    if vulnerability in {"metal_redox_or_cysteine_network", "catalytic_or_nucleotide_site", "protein_or_ligand_interface"}:
        vulnerability_bonus = 0.12
    score = (0.34 * impact) + (0.18 * prime) + (0.18 * biochemical) + (0.12 * charge) + (0.10 * hydro) + vulnerability_bonus
    return float(np.clip(score, 0.0, 1.0) * 100.0)


def _prime_log_ratio_abs(row: pd.Series) -> float:
    ratio = _safe_float(row.get("prime_ratio"), 1.0)
    if ratio <= 0:
        return 0.0
    return float(abs(np.log(ratio)))


def _prime_transition_signature(row: pd.Series) -> str:
    prime_score = _safe_float(row.get("prime_mechanistic_score_percent"))
    prime_diff = _safe_float(row.get("prime_diff"))
    log_ratio = _prime_log_ratio_abs(row)
    gap_delta = abs(_safe_float(row.get("prime_gap_delta")))
    curvature = _safe_float(row.get("prime_curvature_score"))
    if prime_score >= 85.0 or (prime_diff >= 12.0 and log_ratio >= 0.7) or gap_delta >= 6.0 or curvature >= 2.0:
        return "strong_prime_displacement"
    if prime_score >= 70.0 or prime_diff >= 8.0 or log_ratio >= 0.45 or gap_delta >= 4.0 or curvature >= 1.2:
        return "directional_prime_rewiring"
    if prime_diff >= 4.0 or log_ratio >= 0.25:
        return "moderate_prime_shift"
    return "local_prime_adjustment"


def _prime_topology_signature(row: pd.Series) -> str:
    twin_shift = str(row.get("prime_twin_transition") or "0->0")
    sophie_shift = str(row.get("prime_sophie_transition") or "0->0")
    density_delta = abs(_safe_float(row.get("prime_local_density_delta")))
    gap_delta = abs(_safe_float(row.get("prime_gap_delta")))
    if twin_shift != "0->0" or sophie_shift != "0->0":
        return "special_prime_family_transition"
    if gap_delta >= 4.0 or density_delta >= 0.08:
        return "prime_neighborhood_rewiring"
    return "stable_prime_topology"


def _prime_seed_dimensions(row: pd.Series) -> tuple[int, int]:
    vulnerability = str(row.get("quantum_vulnerability_class") or _vulnerability_class(row))
    prime_score = _safe_float(row.get("prime_mechanistic_score_percent"))
    prime_diff = _safe_float(row.get("prime_diff"))
    curvature = _safe_float(row.get("prime_curvature_score"))
    topology = _prime_topology_signature(row)
    if vulnerability == "metal_redox_or_cysteine_network":
        electrons, orbitals = 4, 4
    elif vulnerability == "catalytic_or_nucleotide_site":
        electrons, orbitals = 6, 6
    elif vulnerability in {"protein_or_ligand_interface", "electrostatic_or_dna_binding_surface"}:
        electrons, orbitals = 4, 4
    else:
        electrons, orbitals = 2, 2
    if prime_diff >= 12.0 or prime_score >= 85.0:
        electrons += 2
        orbitals += 2
    elif prime_diff >= 8.0 or prime_score >= 70.0:
        orbitals += 2
    if curvature >= 1.5 or topology == "special_prime_family_transition":
        orbitals += 2
    return min(electrons, 8), min(orbitals, 8)


def _prime_fragment_strategy(row: pd.Series) -> str:
    vulnerability = str(row.get("quantum_vulnerability_class") or _vulnerability_class(row))
    signature = _prime_transition_signature(row)
    topology = _prime_topology_signature(row)
    if vulnerability == "metal_redox_or_cysteine_network":
        return "metal_shell_fragment_plus_first_coordination_layer" if signature == "strong_prime_displacement" else "metal_shell_fragment"
    if vulnerability == "catalytic_or_nucleotide_site":
        return "active_site_fragment_plus_substrate_proxy"
    if vulnerability == "protein_or_ligand_interface":
        return "interface_patch_fragment_with_partner_contact_shell"
    if vulnerability == "electrostatic_or_dna_binding_surface":
        return "charged_surface_cluster_fragment"
    if vulnerability == "folding_stability_or_hydrophobic_core":
        return "packing_core_cluster_fragment_plus_second_shell" if topology == "prime_neighborhood_rewiring" else "packing_core_cluster_fragment"
    return "mutation_centered_fragment"


def _prime_active_space_seed(row: pd.Series) -> str:
    electrons, orbitals = _prime_seed_dimensions(row)
    return f"{electrons}e/{orbitals}o prime-seeded start; expand only if xTB/DFT supports it"


def _prime_qubit_budget_hint(row: pd.Series) -> str:
    _, orbitals = _prime_seed_dimensions(row)
    low_qubits = max(4, (orbitals * 2) - 2)
    high_qubits = max(low_qubits, (orbitals * 2) + 2)
    return f"{low_qubits}-{high_qubits} qubits after mapping/tapering review"


def _prime_shot_schedule(row: pd.Series) -> str:
    prime_ref = max(int(round(_safe_float(row.get("prime_ref"), 2.0))), 2)
    prime_alt = max(int(round(_safe_float(row.get("prime_alt"), 2.0))), 2)
    product_seed = max(prime_ref * prime_alt, 11)
    stage_1 = next_prime(product_seed * 11)
    stage_2 = next_prime(product_seed * 17)
    stage_3 = next_prime(product_seed * 29)
    return f"{stage_1};{stage_2};{stage_3}"


def _prime_guided_sampling_note(row: pd.Series) -> str:
    prime_ref = _safe_float(row.get("prime_ref"))
    prime_alt = _safe_float(row.get("prime_alt"))
    topology = _prime_topology_signature(row)
    if topology == "special_prime_family_transition":
        return "Mutant and reference differ in prime-family topology; preserve matched chemistry, then add a topology-expansion pass only after baseline convergence."
    if prime_alt >= prime_ref:
        return "Mutant prime index expands relative to reference; keep both fragments on the same seed active space, then expand only after matched convergence."
    return "Mutant prime index contracts relative to reference; validate the smallest chemically stable active space first before any expansion."


def _score_prime_quantum_coupling(row: pd.Series) -> float:
    vulnerability = str(row.get("quantum_vulnerability_class") or _vulnerability_class(row))
    prime_score = _safe_float(row.get("prime_mechanistic_score_percent")) / 100.0
    prime_diff = min(_safe_float(row.get("prime_diff")) / 16.0, 1.0)
    log_ratio = min(_prime_log_ratio_abs(row) / 1.2, 1.0)
    gap_delta = min(abs(_safe_float(row.get("prime_gap_delta"))) / 8.0, 1.0)
    curvature = min(_safe_float(row.get("prime_curvature_score")) / 2.5, 1.0)
    density_shift = min(abs(_safe_float(row.get("prime_local_density_delta"))) / 0.25, 1.0)
    charge = min(abs(_safe_float(row.get("charge_abs_diff"))) / 2.0, 1.0)
    hydro = min(abs(_safe_float(row.get("hydro_abs_diff"))) / 5.0, 1.0)
    domain_bonus = 0.06 if str(row.get("domain_known")).lower() in {"true", "1"} else 0.0
    vulnerability_bonus = 0.15 if vulnerability in {"metal_redox_or_cysteine_network", "catalytic_or_nucleotide_site"} else 0.10
    family_bonus = 0.04 if _prime_topology_signature(row) == "special_prime_family_transition" else 0.0
    score = (
        (0.30 * prime_score)
        + (0.18 * prime_diff)
        + (0.14 * log_ratio)
        + (0.08 * gap_delta)
        + (0.06 * curvature)
        + (0.04 * density_shift)
        + (0.08 * charge)
        + (0.06 * hydro)
        + domain_bonus
        + vulnerability_bonus
        + family_bonus
    )
    return float(np.clip(score, 0.0, 1.0) * 100.0)


def _prime_quantum_hypothesis(row: pd.Series) -> str:
    vulnerability = str(row.get("quantum_vulnerability_class") or _vulnerability_class(row))
    signature = _prime_transition_signature(row)
    if vulnerability == "metal_redox_or_cysteine_network":
        return "Prime displacement inside a metal/redox context suggests altered coordination geometry or electron density around the mutant microenvironment."
    if vulnerability == "catalytic_or_nucleotide_site":
        return "Prime-guided fragment expansion should test whether the mutation changes catalytic-state electronics or cofactor handling."
    if vulnerability == "protein_or_ligand_interface":
        return "Prime-guided interface fragments can test whether the mutant redistributes interaction energy across the contact shell."
    if vulnerability == "electrostatic_or_dna_binding_surface":
        return "Prime-guided charged clusters can test whether the mutation redistributes local electrostatics relevant to DNA or partner recognition."
    if signature == "strong_prime_displacement":
        return "Large prime displacement suggests the mutant may require a wider fragment shell to capture mechanistic rewiring beyond a local packing change."
    return "Prime-guided local fragments should test whether the mutation perturbs a focused stability or contact microstate."


def _build_quantum_targets(queue: pd.DataFrame, max_quantum_targets: int) -> pd.DataFrame:
    if queue.empty:
        return pd.DataFrame(
            columns=[
                "quantum_rank",
                "gene",
                "hgvs_p",
                "quantum_priority_score_percent",
                "quantum_vulnerability_class",
                "recommended_quantum_methods",
                "drug_discovery_angle",
            ]
        )
    work = queue.copy()
    for column, default in [
        ("prime_gap_delta", 0.0),
        ("prime_curvature_score", 0.0),
        ("prime_local_density_delta", 0.0),
        ("prime_mod_30_transition", "unknown"),
        ("prime_twin_transition", "0->0"),
        ("prime_sophie_transition", "0->0"),
    ]:
        if column not in work.columns:
            work[column] = default
    work["quantum_priority_score_percent"] = work.apply(lambda row: round(_score_quantum_priority(row), 1), axis=1)
    work["quantum_vulnerability_class"] = work.apply(_vulnerability_class, axis=1)
    work["recommended_quantum_methods"] = work.apply(lambda row: ";".join(_recommended_quantum_methods(row)), axis=1)
    work["drug_discovery_angle"] = work.apply(_drug_discovery_angle, axis=1)
    work["prime_product"] = work.apply(
        lambda row: int(round(_safe_float(row.get("prime_ref"), 0.0))) * int(round(_safe_float(row.get("prime_alt"), 0.0))),
        axis=1,
    )
    work["prime_log_ratio_abs"] = work.apply(lambda row: round(_prime_log_ratio_abs(row), 4), axis=1)
    work["prime_transition_signature"] = work.apply(_prime_transition_signature, axis=1)
    work["prime_topology_signature"] = work.apply(_prime_topology_signature, axis=1)
    work["prime_quantum_coupling_score_percent"] = work.apply(lambda row: round(_score_prime_quantum_coupling(row), 1), axis=1)
    work["prime_fragment_strategy"] = work.apply(_prime_fragment_strategy, axis=1)
    work["prime_active_space_seed"] = work.apply(_prime_active_space_seed, axis=1)
    work["prime_qubit_budget_hint"] = work.apply(_prime_qubit_budget_hint, axis=1)
    work["prime_shot_schedule"] = work.apply(_prime_shot_schedule, axis=1)
    work["prime_quantum_hypothesis"] = work.apply(_prime_quantum_hypothesis, axis=1)
    work["prime_guided_sampling_note"] = work.apply(_prime_guided_sampling_note, axis=1)
    work["qm_region_center"] = work.apply(lambda row: f"{row.get('gene')}:{row.get('position')}:{row.get('aa_ref')}->{row.get('aa_alt')}", axis=1)
    work["suggested_fragment_radius_angstrom"] = work["quantum_vulnerability_class"].map(
        {
            "metal_redox_or_cysteine_network": 8.0,
            "catalytic_or_nucleotide_site": 9.0,
            "protein_or_ligand_interface": 10.0,
            "electrostatic_or_dna_binding_surface": 10.0,
            "folding_stability_or_hydrophobic_core": 7.0,
        }
    ).fillna(8.0)
    work["coordinate_requirement"] = "reference_and_mutant_PDB_or_AF_model_required"
    work["execution_readiness"] = "ready_for_template_generation_requires_coordinates"
    work = work.sort_values(
        ["quantum_priority_score_percent", "prime_mechanistic_score_percent", "protein_impact_score_percent"],
        ascending=[False, False, False],
        kind="stable",
    ).head(max(0, int(max_quantum_targets))).reset_index(drop=True)
    work["quantum_rank"] = list(range(1, len(work) + 1))
    preferred = [
        "quantum_rank",
        "gene",
        "hgvs_p",
        "model_request_id",
        "quantum_priority_score_percent",
        "protein_impact_score_percent",
        "prime_mechanistic_score_percent",
        "prime_ref",
        "prime_alt",
        "prime_diff",
        "prime_ratio",
        "prime_product",
        "prime_log_ratio_abs",
        "prime_gap_delta",
        "prime_curvature_score",
        "prime_local_density_delta",
        "prime_transition_signature",
        "prime_topology_signature",
        "prime_mod_30_transition",
        "prime_twin_transition",
        "prime_sophie_transition",
        "prime_quantum_coupling_score_percent",
        "prime_fragment_strategy",
        "prime_active_space_seed",
        "prime_qubit_budget_hint",
        "prime_shot_schedule",
        "prime_quantum_hypothesis",
        "prime_guided_sampling_note",
        "quantum_vulnerability_class",
        "structural_region",
        "domain_mechanism",
        "mechanism_tags",
        "qm_region_center",
        "suggested_fragment_radius_angstrom",
        "recommended_quantum_methods",
        "recommended_assays",
        "drug_discovery_angle",
        "coordinate_requirement",
        "execution_readiness",
    ]
    return work[[column for column in preferred if column in work.columns]].copy()


def _build_workflow_table(quantum_targets: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if quantum_targets.empty:
        return pd.DataFrame(columns=["workflow_step", "engine", "purpose", "input_requirement", "output_artifact"])
    rows.extend(
        [
            {
                "workflow_step": "1_structure_acquisition",
                "engine": "AlphaFold/PDB/local mutant model",
                "purpose": "Obtain reference and mutant protein coordinates around each prioritized residue.",
                "input_requirement": "Protein sequence, variant, curated model or experimental PDB.",
                "output_artifact": "reference_mutant_structure_pair",
            },
            {
                "workflow_step": "2_local_relaxation",
                "engine": "OpenMM",
                "purpose": "Relax the local mutant microenvironment and detect contact/solvation changes.",
                "input_requirement": "Prepared PDB, force field, solvent or implicit-solvent choice.",
                "output_artifact": "local_md_summary",
            },
            {
                "workflow_step": "3_semiclassical_quantum_screen",
                "engine": "xTB GFN2",
                "purpose": "Fast fragment-level charge, geometry, and interaction-energy screening.",
                "input_requirement": "Fragment XYZ/PDB extracted around the mutation site.",
                "output_artifact": "xtb_fragment_screen",
            },
            {
                "workflow_step": "4_dft_refinement",
                "engine": "Psi4 or equivalent DFT backend",
                "purpose": "Refine top fragments with DFT single-point or constrained optimization.",
                "input_requirement": "Curated QM fragment with protonation and charge state reviewed.",
                "output_artifact": "dft_energy_charge_report",
            },
            {
                "workflow_step": "5_druggability_probe",
                "engine": "AutoDock Vina or ligand-screening backend",
                "purpose": "Probe ligandability of mutant-exposed pockets or interface rescue hypotheses.",
                "input_requirement": "Prepared receptor pocket, ligand library, docking box.",
                "output_artifact": "docking_hotspot_report",
            },
        ]
    )
    return pd.DataFrame(rows)


def _build_prime_quantum_bridge(quantum_targets: pd.DataFrame) -> pd.DataFrame:
    if quantum_targets.empty:
        return pd.DataFrame(
            columns=[
                "quantum_rank",
                "gene",
                "hgvs_p",
                "prime_quantum_coupling_score_percent",
                "prime_transition_signature",
                "prime_active_space_seed",
                "prime_qubit_budget_hint",
                "prime_shot_schedule",
            ]
        )
    preferred = [
        "quantum_rank",
        "gene",
        "hgvs_p",
        "model_request_id",
        "quantum_vulnerability_class",
        "prime_ref",
        "prime_alt",
        "prime_diff",
        "prime_ratio",
        "prime_product",
        "prime_log_ratio_abs",
        "prime_gap_delta",
        "prime_curvature_score",
        "prime_local_density_delta",
        "prime_mechanistic_score_percent",
        "prime_quantum_coupling_score_percent",
        "prime_transition_signature",
        "prime_topology_signature",
        "prime_fragment_strategy",
        "prime_active_space_seed",
        "prime_qubit_budget_hint",
        "prime_shot_schedule",
        "prime_mod_30_transition",
        "prime_twin_transition",
        "prime_sophie_transition",
        "prime_quantum_hypothesis",
        "prime_guided_sampling_note",
    ]
    bridge = quantum_targets[[column for column in preferred if column in quantum_targets.columns]].copy()
    return bridge.sort_values(
        ["prime_quantum_coupling_score_percent", "prime_mechanistic_score_percent", "quantum_rank"],
        ascending=[False, False, True],
        kind="stable",
    ).reset_index(drop=True)


def _template_header(row: pd.Series) -> str:
    return "\n".join(
        [
            f"# PrimeVarClass quantum template for {row.get('gene')} {row.get('hgvs_p')}",
            f"# Quantum rank: {row.get('quantum_rank')}",
            f"# Vulnerability: {row.get('quantum_vulnerability_class')}",
            f"# QM center: {row.get('qm_region_center')}",
            f"# Prime coupling: {row.get('prime_quantum_coupling_score_percent')}% ({row.get('prime_transition_signature')})",
            f"# Prime topology: {row.get('prime_topology_signature')}",
            f"# Prime active-space seed: {row.get('prime_active_space_seed')}",
            f"# Prime shot schedule: {row.get('prime_shot_schedule')}",
            "# Replace placeholder coordinates with a reviewed reference/mutant fragment before execution.",
            "",
        ]
    )


def _write_templates(quantum_targets: pd.DataFrame, template_root: Path) -> list[dict[str, str]]:
    template_root.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    for _, row in quantum_targets.iterrows():
        safe_id = str(row.get("model_request_id") or f"{row.get('gene')}_{row.get('hgvs_p')}").replace(".", "").replace("*", "Ter")
        psi4_path = template_root / f"{safe_id}.psi4.in"
        xtb_path = template_root / f"{safe_id}.xtb.sh"
        openmm_path = template_root / f"{safe_id}.openmm_plan.py"
        vina_path = template_root / f"{safe_id}.vina_config.txt"
        header = _template_header(row)
        psi4_path.write_text(
            header
            + "memory 4 GB\n"
            + "set basis 6-31G*\n"
            + "set scf_type df\n"
            + "molecule mutant_fragment {\n"
            + "  0 1\n"
            + "  # Paste QM fragment coordinates here.\n"
            + "}\n\n"
            + "energy('B3LYP-D3BJ')\n",
            encoding="utf-8",
        )
        xtb_path.write_text(
            header
            + "xtb mutant_fragment.xyz --gfn 2 --opt --alpb water > xtb_mutant_fragment.log\n",
            encoding="utf-8",
        )
        openmm_path.write_text(
            header
            + "from pathlib import Path\n"
            + "# TODO: load prepared reference/mutant PDB, run local restrained relaxation, export contact deltas.\n"
            + "structure_path = Path('mutant_prepared.pdb')\n"
            + "print(f'Prepare OpenMM local relaxation for {structure_path}')\n",
            encoding="utf-8",
        )
        vina_path.write_text(
            header
            + "receptor = mutant_receptor.pdbqt\n"
            + "ligand = candidate_ligand.pdbqt\n"
            + f"center_x = 0  # replace with coordinates around residue {row.get('qm_region_center')}\n"
            + "center_y = 0\n"
            + "center_z = 0\n"
            + "size_x = 20\nsize_y = 20\nsize_z = 20\nexhaustiveness = 16\n",
            encoding="utf-8",
        )
        rows.append(
            {
                "model_request_id": safe_id,
                "psi4_template_path": str(psi4_path),
                "xtb_template_path": str(xtb_path),
                "openmm_template_path": str(openmm_path),
                "vina_template_path": str(vina_path),
            }
        )
    return rows


def _vqe_plan_for_target(row: pd.Series) -> dict[str, Any]:
    vulnerability = str(row.get("quantum_vulnerability_class") or "")
    prime_seed = str(row.get("prime_active_space_seed") or "")
    if vulnerability == "metal_redox_or_cysteine_network":
        active_space = "metal/cysteine side-chain fragment; start 4e/4o then expand after classical DFT"
        ansatz = "UCCSD_then_ADAPT_VQE"
        optimizer = "COBYLA_for_simulator_then_SPSA_for_noisy_backend"
    elif vulnerability == "catalytic_or_nucleotide_site":
        active_space = "catalytic residue plus substrate/cofactor proxy; start 6e/6o"
        ansatz = "UCCSD_or_kUpCCGSD"
        optimizer = "SLSQP_or_L-BFGS-B_for_simulator"
    elif vulnerability == "electrostatic_or_dna_binding_surface":
        active_space = "charged side-chain cluster; start 2e/2o or 4e/4o"
        ansatz = "hardware_efficient_then_UCC_refinement"
        optimizer = "COBYLA"
    else:
        active_space = "mutation-centered side-chain fragment; start 2e/2o"
        ansatz = "hardware_efficient_screen_then_UCCSD"
        optimizer = "COBYLA"
    return {
        "active_space_recommendation": f"{active_space}; prime seed: {prime_seed}" if prime_seed else active_space,
        "fermion_to_qubit_mapping": "Jordan-Wigner primary; parity/tapering optional after symmetry review",
        "recommended_ansatz": ansatz,
        "recommended_optimizer": optimizer,
        "simulator_backend": "statevector_or_shot_based_simulator_first",
        "hardware_backend": "NISQ_backend_only_after_noise_and_resource_estimate",
        "minimum_validation_baseline": "compare_against_xTB_and_DFT_fragment_energy_before_interpreting_VQE",
        "prime_guided_initialization": f"Use prime seed {prime_seed} with shot ladder {row.get('prime_shot_schedule')}" if prime_seed else "Keep mutant and reference on matched active spaces.",
        "prime_guided_seed_strategy": str(row.get("prime_guided_sampling_note") or ""),
    }


def _build_vqe_targets(quantum_targets: pd.DataFrame) -> pd.DataFrame:
    if quantum_targets.empty:
        return pd.DataFrame(
            columns=[
                "vqe_rank",
                "gene",
                "hgvs_p",
                "vqe_readiness_score_percent",
                "recommended_ansatz",
                "active_space_recommendation",
            ]
        )
    rows: list[dict[str, Any]] = []
    for _, row in quantum_targets.iterrows():
        plan = _vqe_plan_for_target(row)
        quantum_priority = _safe_float(row.get("quantum_priority_score_percent")) / 100.0
        prime_score = _safe_float(row.get("prime_mechanistic_score_percent")) / 100.0
        impact_score = _safe_float(row.get("protein_impact_score_percent")) / 100.0
        coupling_score = _safe_float(row.get("prime_quantum_coupling_score_percent")) / 100.0
        vulnerability = str(row.get("quantum_vulnerability_class") or "")
        vqe_bonus = 0.12 if vulnerability in {"metal_redox_or_cysteine_network", "catalytic_or_nucleotide_site"} else 0.05
        prime_guided_bonus = 0.05 if coupling_score >= 0.85 else (0.02 if coupling_score >= 0.7 else 0.0)
        readiness = float(
            np.clip(
                (0.30 * quantum_priority) + (0.18 * prime_score) + (0.18 * impact_score) + (0.24 * coupling_score) + vqe_bonus + prime_guided_bonus,
                0.0,
                1.0,
            )
            * 100.0
        )
        rows.append(
            {
                **{column: row.get(column) for column in quantum_targets.columns},
                **plan,
                "vqe_readiness_score_percent": round(readiness, 1),
                "vqe_question": "Does the mutant fragment shift the ground-state electronic structure enough to explain altered stability, binding, or druggability?",
                "vqe_interpretation_guardrail": "Interpret only against xTB/DFT baselines and experimentally reviewed protonation/charge states.",
            }
        )
    table = pd.DataFrame(rows).sort_values(
        ["vqe_readiness_score_percent", "quantum_priority_score_percent", "prime_mechanistic_score_percent"],
        ascending=[False, False, False],
        kind="stable",
    ).reset_index(drop=True)
    table["vqe_rank"] = list(range(1, len(table) + 1))
    preferred = [
        "vqe_rank",
        "gene",
        "hgvs_p",
        "model_request_id",
        "vqe_readiness_score_percent",
        "quantum_priority_score_percent",
        "prime_mechanistic_score_percent",
        "prime_quantum_coupling_score_percent",
        "prime_gap_delta",
        "prime_curvature_score",
        "prime_local_density_delta",
        "prime_transition_signature",
        "prime_topology_signature",
        "prime_fragment_strategy",
        "prime_active_space_seed",
        "prime_qubit_budget_hint",
        "prime_shot_schedule",
        "prime_mod_30_transition",
        "prime_twin_transition",
        "prime_sophie_transition",
        "quantum_vulnerability_class",
        "active_space_recommendation",
        "fermion_to_qubit_mapping",
        "recommended_ansatz",
        "recommended_optimizer",
        "simulator_backend",
        "hardware_backend",
        "minimum_validation_baseline",
        "prime_guided_initialization",
        "prime_guided_seed_strategy",
        "vqe_question",
        "vqe_interpretation_guardrail",
    ]
    return table[[column for column in preferred if column in table.columns]].copy()


def _build_algorithm_portfolio(vqe_targets: pd.DataFrame) -> pd.DataFrame:
    target_count = int(len(vqe_targets))
    mean_vqe = round(float(vqe_targets["vqe_readiness_score_percent"].mean()), 1) if target_count else 0.0
    mean_coupling = round(float(vqe_targets["prime_quantum_coupling_score_percent"].mean()), 1) if target_count and "prime_quantum_coupling_score_percent" in vqe_targets.columns else 0.0
    return pd.DataFrame(
        [
            {
                "algorithm": "prime_guided_initialization",
                "readiness_tier": "active_methodological_layer" if target_count else "pending_targets",
                "best_use": "Use prime-derived transition classes, active-space seeds, and shot ladders to compare mutant and reference fragments under matched workflows.",
                "backend_family": "heuristic layer over Qiskit Nature; PennyLane; OpenFermion",
                "target_count": target_count,
                "mean_readiness_score_percent": mean_coupling,
            },
            {
                "algorithm": "VQE",
                "readiness_tier": "immediate_template_ready" if target_count else "pending_targets",
                "best_use": "Estimate ground-state fragment energy shifts for mutation-centered QM fragments.",
                "backend_family": "Qiskit Nature; PennyLane qchem; OpenFermion/PySCF",
                "target_count": target_count,
                "mean_readiness_score_percent": mean_vqe,
            },
            {
                "algorithm": "ADAPT-VQE",
                "readiness_tier": "recommended_for_high_value_targets" if target_count else "pending_targets",
                "best_use": "Reduce ansatz overhead for chemically structured active spaces after VQE screening.",
                "backend_family": "Qiskit/PennyLane/OpenFermion-compatible workflow",
                "target_count": min(target_count, 6),
                "mean_readiness_score_percent": mean_vqe,
            },
            {
                "algorithm": "VQD",
                "readiness_tier": "secondary_hypothesis_layer",
                "best_use": "Explore low-lying excited-state sensitivity only after ground-state VQE is stable.",
                "backend_family": "PennyLane or custom variational workflow",
                "target_count": min(target_count, 4),
                "mean_readiness_score_percent": max(mean_vqe - 8.0, 0.0),
            },
            {
                "algorithm": "QPE",
                "readiness_tier": "fault_tolerant_future_reference",
                "best_use": "Long-term benchmark for precise phase/energy estimation when hardware supports it.",
                "backend_family": "future fault-tolerant quantum stack",
                "target_count": 0,
                "mean_readiness_score_percent": 0.0,
            },
            {
                "algorithm": "classical_QM_crosscheck",
                "readiness_tier": "mandatory_control",
                "best_use": "xTB/DFT baselines required before any quantum-computing claim.",
                "backend_family": "xTB; Psi4; PySCF",
                "target_count": target_count,
                "mean_readiness_score_percent": 100.0 if target_count else 0.0,
            },
        ]
    )


def _write_vqe_templates(vqe_targets: pd.DataFrame, template_root: Path) -> list[dict[str, str]]:
    template_root.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    for _, row in vqe_targets.iterrows():
        safe_id = str(row.get("model_request_id") or f"{row.get('gene')}_{row.get('hgvs_p')}").replace(".", "").replace("*", "Ter")
        qiskit_path = template_root / f"{safe_id}.qiskit_nature_vqe.py"
        pennylane_path = template_root / f"{safe_id}.pennylane_vqe.py"
        openfermion_path = template_root / f"{safe_id}.openfermion_vqe_plan.py"
        header = "\n".join(
            [
                f"# PrimeVarClass VQE template for {row.get('gene')} {row.get('hgvs_p')}",
                f"# VQE rank: {row.get('vqe_rank')}",
                f"# Active space: {row.get('active_space_recommendation')}",
                f"# Ansatz: {row.get('recommended_ansatz')}",
                f"# Prime coupling: {row.get('prime_quantum_coupling_score_percent')}% ({row.get('prime_transition_signature')})",
                f"# Prime shot schedule: {row.get('prime_shot_schedule')}",
                "# Fill fragment geometry, charge, multiplicity, active space, and backend before execution.",
                "",
            ]
        )
        qiskit_path.write_text(
            header
            + "from qiskit_algorithms import VQE\n"
            + "from qiskit_algorithms.optimizers import COBYLA\n"
            + "from qiskit.primitives import Estimator\n"
            + "from qiskit_nature.second_q.mappers import JordanWignerMapper\n"
            + "# TODO: build ElectronicStructureProblem from a reviewed molecular driver.\n"
            + f"# Prime-guided initialization: {row.get('prime_guided_initialization')}\n"
            + "mapper = JordanWignerMapper()\n"
            + "optimizer = COBYLA(maxiter=500)\n"
            + "# ansatz = ...  # UCCSD or hardware-efficient circuit after active-space review\n"
            + "# vqe = VQE(Estimator(), ansatz, optimizer)\n",
            encoding="utf-8",
        )
        pennylane_path.write_text(
            header
            + "import pennylane as qml\n"
            + "from pennylane import qchem\n"
            + "# TODO: define symbols, coordinates, charge, multiplicity, and active space.\n"
            + f"# Prime-guided seed strategy: {row.get('prime_guided_seed_strategy')}\n"
            + "# hamiltonian, qubits = qchem.molecular_hamiltonian(symbols, coordinates)\n"
            + "# dev = qml.device('default.qubit', wires=qubits)\n"
            + "# Build ansatz and optimize expectation value with a classical optimizer.\n",
            encoding="utf-8",
        )
        openfermion_path.write_text(
            header
            + "from openfermion.transforms import jordan_wigner\n"
            + "# TODO: generate molecular Hamiltonian with PySCF/Psi4, freeze core, choose active space.\n"
            + f"# Prime qubit budget hint: {row.get('prime_qubit_budget_hint')}\n"
            + "# qubit_hamiltonian = jordan_wigner(fermion_hamiltonian)\n"
            + "# Export to a simulator/VQE stack and compare against xTB/DFT controls.\n",
            encoding="utf-8",
        )
        rows.append(
            {
                "model_request_id": safe_id,
                "qiskit_nature_vqe_template_path": str(qiskit_path),
                "pennylane_vqe_template_path": str(pennylane_path),
                "openfermion_vqe_template_path": str(openfermion_path),
            }
        )
    return rows


def _build_markdown(bundle: dict[str, Any]) -> str:
    summary = bundle["summary"]
    targets = bundle["quantum_targets"]
    workflow = bundle["workflow_table"]
    bridge = bundle.get("prime_quantum_bridge")
    bridge_df = bridge if isinstance(bridge, pd.DataFrame) else pd.DataFrame()
    vqe_targets = bundle.get("vqe_targets")
    vqe_df = vqe_targets if isinstance(vqe_targets, pd.DataFrame) else pd.DataFrame()
    lines = [
        "# PrimeVarClass Quantum Proteomics Engine",
        "",
        f"- Generated at: `{summary['generated_at']}`",
        f"- Quantum targets: `{summary['quantum_target_count']}`",
        f"- High-priority QM targets: `{summary['high_priority_quantum_target_count']}`",
        f"- Mean quantum priority: `{summary['mean_quantum_priority_score_percent']}%`",
        f"- Mean prime score in QM targets: `{summary['mean_prime_mechanistic_score_percent']}%`",
        f"- Mean prime-quantum coupling: `{summary['mean_prime_quantum_coupling_score_percent']}%`",
        f"- Top vulnerability classes: `{', '.join(summary['top_vulnerability_classes']) if summary['top_vulnerability_classes'] else 'none'}`",
        "",
        "## Top quantum targets",
        "",
    ]
    if targets.empty:
        lines.append("- No quantum targets available.")
    else:
        for row in targets.head(12).to_dict(orient="records"):
            lines.append(
                "- "
                f"{row.get('gene')} {row.get('hgvs_p')}: "
                f"QM={row.get('quantum_priority_score_percent')}%, "
                f"prime={row.get('prime_mechanistic_score_percent')}%, "
                f"class={row.get('quantum_vulnerability_class')}, "
                f"methods={row.get('recommended_quantum_methods')}"
            )
    lines.extend(["", "## Prime-quantum bridge", ""])
    if bridge_df.empty:
        lines.append("- No prime-quantum bridge targets available.")
    else:
        for row in bridge_df.head(8).to_dict(orient="records"):
            lines.append(
                "- "
                f"{row.get('gene')} {row.get('hgvs_p')}: "
                f"prime-Q={row.get('prime_quantum_coupling_score_percent')}%, "
                f"signature={row.get('prime_transition_signature')}, "
                f"seed={row.get('prime_active_space_seed')}, "
                f"shots={row.get('prime_shot_schedule')}"
            )
    lines.extend(["", "## VQE and quantum algorithm targets", ""])
    if vqe_df.empty:
        lines.append("- No VQE targets available.")
    else:
        for row in vqe_df.head(8).to_dict(orient="records"):
            lines.append(
                "- "
                f"{row.get('gene')} {row.get('hgvs_p')}: "
                f"VQE readiness={row.get('vqe_readiness_score_percent')}%, "
                f"ansatz={row.get('recommended_ansatz')}, "
                f"mapping={row.get('fermion_to_qubit_mapping')}, "
                f"prime-guided={row.get('prime_guided_initialization')}"
            )
    lines.extend(["", "## Execution workflow", ""])
    for row in workflow.to_dict(orient="records"):
        lines.append(
            "- "
            f"{row.get('workflow_step')} ({row.get('engine')}): "
            f"{row.get('purpose')}"
        )
    lines.extend(
        [
            "",
            "## Scientific guardrails",
            "",
            "- This engine prioritizes quantum/structural hypotheses; it does not claim therapeutic efficacy.",
            "- Coordinates, protonation states, charge states, and experimental controls must be reviewed before running QM, MD, or docking.",
            "- Drug-development hypotheses require orthogonal biochemical, cellular, and translational validation.",
        ]
    )
    return "\n".join(lines).strip()


def build_quantum_proteomics_package(
    *,
    protein_impact_manifest_path: str,
    max_quantum_targets: int = 12,
) -> dict[str, Any]:
    manifest = _load_manifest(protein_impact_manifest_path)
    queue = _read_table(manifest.get("modeling_queue_path"))
    targets = _build_quantum_targets(queue, max_quantum_targets=max_quantum_targets)
    prime_quantum_bridge = _build_prime_quantum_bridge(targets)
    vqe_targets = _build_vqe_targets(targets)
    algorithm_portfolio = _build_algorithm_portfolio(vqe_targets)
    workflow = _build_workflow_table(targets)
    top_classes = targets["quantum_vulnerability_class"].value_counts().head(5).index.tolist() if not targets.empty else []
    summary = {
        "generated_at": _now_utc(),
        "quantum_target_count": int(len(targets)),
        "high_priority_quantum_target_count": int((targets["quantum_priority_score_percent"] >= 85.0).sum()) if not targets.empty else 0,
        "vqe_target_count": int(len(vqe_targets)),
        "high_readiness_vqe_target_count": int((vqe_targets["vqe_readiness_score_percent"] >= 85.0).sum()) if not vqe_targets.empty else 0,
        "mean_quantum_priority_score_percent": round(float(targets["quantum_priority_score_percent"].mean()), 1) if not targets.empty else 0.0,
        "mean_vqe_readiness_score_percent": round(float(vqe_targets["vqe_readiness_score_percent"].mean()), 1) if not vqe_targets.empty else 0.0,
        "mean_prime_mechanistic_score_percent": round(float(targets["prime_mechanistic_score_percent"].mean()), 1) if not targets.empty and "prime_mechanistic_score_percent" in targets.columns else 0.0,
        "mean_prime_quantum_coupling_score_percent": round(float(targets["prime_quantum_coupling_score_percent"].mean()), 1) if not targets.empty and "prime_quantum_coupling_score_percent" in targets.columns else 0.0,
        "high_prime_quantum_coupling_target_count": int((targets["prime_quantum_coupling_score_percent"] >= 85.0).sum()) if not targets.empty and "prime_quantum_coupling_score_percent" in targets.columns else 0,
        "top_vulnerability_classes": top_classes,
        "source_protein_impact_manifest_path": str(Path(protein_impact_manifest_path).expanduser().resolve()),
    }
    bundle = {
        "summary": summary,
        "quantum_targets": targets,
        "prime_quantum_bridge": prime_quantum_bridge,
        "vqe_targets": vqe_targets,
        "algorithm_portfolio": algorithm_portfolio,
        "workflow_table": workflow,
        "source_manifest": manifest,
    }
    bundle["markdown_report"] = _build_markdown(bundle)
    bundle["html_report"] = _render_markdown_html(bundle["markdown_report"], "PrimeVarClass Quantum Proteomics Engine")
    return bundle


def export_quantum_proteomics_package(
    *,
    protein_impact_manifest_path: str,
    output_dir: str,
    max_quantum_targets: int = 12,
) -> dict[str, Any]:
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    templates_root = output_root / "quantum_job_templates"
    vqe_templates_root = output_root / "vqe_job_templates"
    bundle = build_quantum_proteomics_package(
        protein_impact_manifest_path=protein_impact_manifest_path,
        max_quantum_targets=max_quantum_targets,
    )
    targets = bundle["quantum_targets"]
    prime_quantum_bridge = bundle["prime_quantum_bridge"]
    vqe_targets = bundle["vqe_targets"]
    algorithm_portfolio = bundle["algorithm_portfolio"]
    workflow = bundle["workflow_table"]
    templates = _write_templates(targets, templates_root)
    vqe_templates = _write_vqe_templates(vqe_targets, vqe_templates_root)

    manifest_path = output_root / "quantum_proteomics_manifest.json"
    targets_path = output_root / "quantum_targets.csv"
    prime_quantum_bridge_path = output_root / "prime_quantum_bridge.csv"
    vqe_targets_path = output_root / "vqe_targets.csv"
    algorithm_portfolio_path = output_root / "quantum_algorithm_portfolio.csv"
    workflow_path = output_root / "quantum_workflow.csv"
    templates_path = output_root / "quantum_job_templates.csv"
    vqe_templates_path = output_root / "vqe_job_templates.csv"
    markdown_path = output_root / "quantum_proteomics_report.md"
    html_path = output_root / "quantum_proteomics_report.html"

    targets.to_csv(targets_path, index=False)
    prime_quantum_bridge.to_csv(prime_quantum_bridge_path, index=False)
    vqe_targets.to_csv(vqe_targets_path, index=False)
    algorithm_portfolio.to_csv(algorithm_portfolio_path, index=False)
    workflow.to_csv(workflow_path, index=False)
    pd.DataFrame(templates).to_csv(templates_path, index=False)
    pd.DataFrame(vqe_templates).to_csv(vqe_templates_path, index=False)
    markdown_path.write_text(str(bundle.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(str(bundle.get("html_report") or ""), encoding="utf-8")

    manifest_payload = {
        "generated_at": _now_utc(),
        "summary": bundle.get("summary") or {},
        "source_protein_impact_manifest_path": str(Path(protein_impact_manifest_path).expanduser().resolve()),
        "quantum_targets_path": str(targets_path),
        "prime_quantum_bridge_path": str(prime_quantum_bridge_path),
        "vqe_targets_path": str(vqe_targets_path),
        "quantum_algorithm_portfolio_path": str(algorithm_portfolio_path),
        "quantum_workflow_path": str(workflow_path),
        "quantum_job_templates_path": str(templates_path),
        "quantum_job_templates_dir": str(templates_root),
        "vqe_job_templates_path": str(vqe_templates_path),
        "vqe_job_templates_dir": str(vqe_templates_root),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
    }
    manifest_path.write_text(json.dumps(_jsonify(manifest_payload), indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "quantum_proteomics_package": bundle,
        "quantum_proteomics_manifest_path": str(manifest_path),
        "quantum_targets_path": str(targets_path),
        "prime_quantum_bridge_path": str(prime_quantum_bridge_path),
        "vqe_targets_path": str(vqe_targets_path),
        "quantum_algorithm_portfolio_path": str(algorithm_portfolio_path),
        "quantum_workflow_path": str(workflow_path),
        "quantum_job_templates_path": str(templates_path),
        "quantum_job_templates_dir": str(templates_root),
        "vqe_job_templates_path": str(vqe_templates_path),
        "vqe_job_templates_dir": str(vqe_templates_root),
        "quantum_proteomics_report_markdown_path": str(markdown_path),
        "quantum_proteomics_report_html_path": str(html_path),
    }
