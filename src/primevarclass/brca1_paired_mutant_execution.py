from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .brca1_engine_execution import _engine_paths
from .brca1_fragment_preparation import _parse_hgvs_p, _parse_pdb_atoms, _run_xtb, _write_pdb, _write_xyz
from .real_data_preparation import _jsonify, _render_markdown_html


BACKBONE_ATOMS = {"N", "CA", "C", "O", "OXT"}
RESIDUE_NAME = {
    "Ala": "ALA",
    "Arg": "ARG",
    "Asn": "ASN",
    "Asp": "ASP",
    "Cys": "CYS",
    "Gln": "GLN",
    "Glu": "GLU",
    "Gly": "GLY",
    "His": "HIS",
    "Ile": "ILE",
    "Leu": "LEU",
    "Lys": "LYS",
    "Met": "MET",
    "Phe": "PHE",
    "Pro": "PRO",
    "Ser": "SER",
    "Thr": "THR",
    "Trp": "TRP",
    "Tyr": "TYR",
    "Val": "VAL",
}


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _percent(value: Any, default: int = 0) -> int:
    try:
        numeric = float(value)
    except Exception:
        return default
    if np.isnan(numeric) or np.isinf(numeric):
        return default
    return max(0, min(100, int(round(numeric))))


def _read_table(path_value: str | Path | None) -> pd.DataFrame:
    if not path_value:
        return pd.DataFrame()
    path = Path(path_value).expanduser()
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def _unit(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm < 1e-8:
        return np.array([1.0, 0.0, 0.0])
    return vector / norm


def _row_coords(row: pd.Series) -> np.ndarray:
    return np.array([float(row["x"]), float(row["y"]), float(row["z"])], dtype=float)


def _target_basis(target: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None:
    by_atom = {str(row["atom_name"]).strip(): row for _, row in target.iterrows()}
    ca = by_atom.get("CA")
    if ca is None:
        return None
    ca_coords = _row_coords(ca)
    if "CB" in by_atom:
        e1 = _unit(_row_coords(by_atom["CB"]) - ca_coords)
    elif "C" in by_atom and "N" in by_atom:
        e1 = _unit((_row_coords(by_atom["C"]) - ca_coords) + (ca_coords - _row_coords(by_atom["N"])))
    else:
        e1 = np.array([1.0, 0.0, 0.0])
    helper = np.array([0.0, 0.0, 1.0])
    if "C" in by_atom:
        helper = _row_coords(by_atom["C"]) - ca_coords
    e2 = np.cross(e1, helper)
    if float(np.linalg.norm(e2)) < 1e-8:
        e2 = np.cross(e1, np.array([0.0, 1.0, 0.0]))
    e2 = _unit(e2)
    e3 = _unit(np.cross(e1, e2))
    return ca_coords, e1, e2, e3


def _sidechain_specs(residue: str) -> list[tuple[str, str, float, float, float]]:
    # Coordinates are idealized heavy-atom draft positions in a local CA/CB frame.
    specs: dict[str, list[tuple[str, str, float, float, float]]] = {
        "ALA": [("CB", "C", 1.53, 0.00, 0.00)],
        "ASP": [("CB", "C", 1.53, 0.00, 0.00), ("CG", "C", 2.95, 0.00, 0.00), ("OD1", "O", 3.55, 1.05, 0.00), ("OD2", "O", 3.55, -1.05, 0.00)],
        "ASN": [("CB", "C", 1.53, 0.00, 0.00), ("CG", "C", 2.95, 0.00, 0.00), ("OD1", "O", 3.55, 1.05, 0.00), ("ND2", "N", 3.55, -1.05, 0.00)],
        "GLU": [("CB", "C", 1.53, 0.00, 0.00), ("CG", "C", 2.95, 0.00, 0.00), ("CD", "C", 4.35, 0.00, 0.00), ("OE1", "O", 4.95, 1.05, 0.00), ("OE2", "O", 4.95, -1.05, 0.00)],
        "GLN": [("CB", "C", 1.53, 0.00, 0.00), ("CG", "C", 2.95, 0.00, 0.00), ("CD", "C", 4.35, 0.00, 0.00), ("OE1", "O", 4.95, 1.05, 0.00), ("NE2", "N", 4.95, -1.05, 0.00)],
        "LYS": [("CB", "C", 1.53, 0.00, 0.00), ("CG", "C", 2.95, 0.15, 0.00), ("CD", "C", 4.35, -0.05, 0.15), ("CE", "C", 5.75, 0.10, -0.10), ("NZ", "N", 7.10, 0.00, 0.00)],
        "HIS": [("CB", "C", 1.53, 0.00, 0.00), ("CG", "C", 2.65, 0.00, 0.00), ("ND1", "N", 3.35, 0.85, 0.00), ("CD2", "C", 3.35, -0.85, 0.00), ("CE1", "C", 4.45, 0.45, 0.00), ("NE2", "N", 4.45, -0.45, 0.00)],
        "VAL": [("CB", "C", 1.53, 0.00, 0.00), ("CG1", "C", 2.45, 0.95, 0.00), ("CG2", "C", 2.45, -0.95, 0.00)],
        "LEU": [("CB", "C", 1.53, 0.00, 0.00), ("CG", "C", 2.95, 0.00, 0.00), ("CD1", "C", 3.85, 0.95, 0.00), ("CD2", "C", 3.85, -0.95, 0.00)],
        "GLY": [],
    }
    return specs.get(residue, [])


def _mutate_fragment_atoms(reference_atoms: pd.DataFrame, position: int, alt_three_letter: str) -> tuple[pd.DataFrame, str]:
    if reference_atoms.empty:
        return pd.DataFrame(), "missing_reference_fragment"
    target = reference_atoms.loc[reference_atoms["resseq"].astype(int).eq(int(position))].copy()
    if target.empty:
        return pd.DataFrame(), "missing_target_residue"
    residue_name = RESIDUE_NAME.get(str(alt_three_letter), str(alt_three_letter).upper()[:3])
    basis = _target_basis(target)
    if basis is None:
        return pd.DataFrame(), "missing_target_backbone"
    ca_coords, e1, e2, e3 = basis
    target_backbone = target.loc[target["atom_name"].astype(str).str.strip().isin(BACKBONE_ATOMS)].copy()
    if target_backbone.empty:
        return pd.DataFrame(), "missing_target_backbone"
    target_backbone["res_name"] = residue_name
    template = target_backbone.iloc[0].to_dict()
    sidechain_rows: list[dict[str, Any]] = []
    for atom_name, element, along, lateral, vertical in _sidechain_specs(residue_name):
        coords = ca_coords + e1 * along + e2 * lateral + e3 * vertical
        row = dict(template)
        row.update(
            {
                "atom_name": atom_name,
                "res_name": residue_name,
                "x": float(coords[0]),
                "y": float(coords[1]),
                "z": float(coords[2]),
                "element": element,
            }
        )
        sidechain_rows.append(row)
    other_atoms = reference_atoms.loc[~reference_atoms["resseq"].astype(int).eq(int(position))].copy()
    mutant = pd.concat([other_atoms, target_backbone, pd.DataFrame(sidechain_rows)], ignore_index=True, sort=False)
    mutant = mutant.sort_values(["chain_id", "resseq", "serial"], kind="stable").reset_index(drop=True)
    return mutant, "draft_sidechain_substitution"


def _build_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# PrimeVarClass BRCA1 Paired Mutant Execution",
        "",
        f"- Generated at: `{summary.get('generated_at')}`",
        f"- Targets requested: `{summary.get('target_count')}`",
        f"- Draft mutant coordinates generated: `{summary.get('draft_mutant_coordinate_count')}`",
        f"- Paired xTB attempted: `{summary.get('paired_xtb_attempted_count')}`",
        f"- Paired xTB completed: `{summary.get('paired_xtb_completed_count')}`",
        f"- Paired execution readiness: `{summary.get('paired_mutant_execution_readiness_percent')}%`",
        "",
        "## Scientific boundary",
        "",
        "- Mutant coordinates are deterministic draft side-chain substitutions for triage.",
        "- They are not rotamer-reviewed, protonation-reviewed, MD-relaxed mutant structures.",
        "- Paired xTB deltas are screening signals and must not be interpreted as definitive pathogenic or drug-response mechanisms.",
    ]
    return "\n".join(lines).strip()


def build_brca1_paired_mutant_execution_package(
    *,
    brca1_fragment_preparation_manifest_path: str,
    execute_xtb: bool = True,
    max_pairs: int = 3,
    xtb_timeout_sec: int = 240,
) -> dict[str, Any]:
    manifest = json.loads(Path(brca1_fragment_preparation_manifest_path).read_text(encoding="utf-8"))
    prepared_table = _read_table(manifest.get("prepared_fragment_table_path"))
    summary_seed = manifest.get("summary") or {}
    return {
        "summary_seed": {
            "generated_at": _now_utc(),
            "target_count": int(len(prepared_table)),
            "source_fragment_manifest_path": str(Path(brca1_fragment_preparation_manifest_path).expanduser().resolve()),
            "source_prepared_fragment_count": int(summary_seed.get("prepared_fragment_count") or 0),
            "execute_xtb": bool(execute_xtb),
            "max_pairs": int(max_pairs),
            "xtb_timeout_sec": int(xtb_timeout_sec),
        },
        "prepared_table": prepared_table,
        "engine_paths": manifest.get("engine_paths") or _engine_paths(),
        "execute_xtb": bool(execute_xtb),
        "max_pairs": int(max_pairs),
        "xtb_timeout_sec": int(xtb_timeout_sec),
    }


def export_brca1_paired_mutant_execution_package(
    *,
    brca1_fragment_preparation_manifest_path: str,
    output_dir: str,
    execute_xtb: bool = True,
    max_pairs: int = 3,
    xtb_timeout_sec: int = 240,
) -> dict[str, Any]:
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    payload = build_brca1_paired_mutant_execution_package(
        brca1_fragment_preparation_manifest_path=brca1_fragment_preparation_manifest_path,
        execute_xtb=execute_xtb,
        max_pairs=max_pairs,
        xtb_timeout_sec=xtb_timeout_sec,
    )
    pairs_dir = output_root / "paired_mutant_fragments"
    pairs_dir.mkdir(parents=True, exist_ok=True)
    prepared = payload["prepared_table"]
    engine_paths = payload["engine_paths"]
    xtb_path = str(engine_paths.get("xtb") or "")
    rows: list[dict[str, Any]] = []
    xtb_logs: list[dict[str, Any]] = []
    attempted_pairs = 0
    for _, row in prepared.iterrows():
        if str(row.get("preparation_status") or "") != "prepared_reference_fragment":
            continue
        model_id = str(row.get("model_request_id") or "").strip()
        hgvs_p = str(row.get("hgvs_p") or "")
        parsed = _parse_hgvs_p(hgvs_p)
        position = parsed.get("position")
        alt = str(parsed.get("aa_alt") or "")
        reference_path = Path(str(row.get("reference_fragment_pdb_path") or ""))
        reference_atoms = _parse_pdb_atoms(reference_path) if reference_path.exists() else pd.DataFrame()
        mutant_atoms, mutation_status = _mutate_fragment_atoms(reference_atoms, int(position or 0), alt)
        model_dir = pairs_dir / model_id
        model_dir.mkdir(parents=True, exist_ok=True)
        reference_pair_pdb = model_dir / f"{model_id}.paired_reference_fragment.pdb"
        reference_pair_xyz = model_dir / f"{model_id}.paired_reference_fragment.xyz"
        mutant_pdb = model_dir / f"{model_id}.draft_mutant_fragment.pdb"
        mutant_xyz = model_dir / f"{model_id}.draft_mutant_fragment.xyz"
        reference_status = "not_attempted"
        mutant_status = "not_attempted"
        reference_energy = None
        mutant_energy = None
        if not reference_atoms.empty:
            _write_pdb(reference_atoms, reference_pair_pdb)
            _write_xyz(reference_atoms, reference_pair_xyz, f"{model_id} paired reference fragment")
        if not mutant_atoms.empty:
            _write_pdb(mutant_atoms, mutant_pdb)
            _write_xyz(mutant_atoms, mutant_xyz, f"{model_id} draft mutant fragment")
        pair_should_run = bool(payload["execute_xtb"] and xtb_path and not reference_atoms.empty and not mutant_atoms.empty and attempted_pairs < int(payload["max_pairs"]))
        if pair_should_run:
            reference_result = _run_xtb(xtb_path, reference_pair_xyz, model_dir, timeout_sec=int(payload["xtb_timeout_sec"]))
            reference_result.update({"model_request_id": model_id, "fragment_kind": "reference", "xyz_path": str(reference_pair_xyz)})
            xtb_logs.append(reference_result)
            mutant_result = _run_xtb(xtb_path, mutant_xyz, model_dir, timeout_sec=int(payload["xtb_timeout_sec"]))
            mutant_result.update({"model_request_id": model_id, "fragment_kind": "draft_mutant", "xyz_path": str(mutant_xyz)})
            xtb_logs.append(mutant_result)
            reference_status = str(reference_result.get("status") or "")
            mutant_status = str(mutant_result.get("status") or "")
            reference_energy = reference_result.get("total_energy_hartree")
            mutant_energy = mutant_result.get("total_energy_hartree")
            attempted_pairs += 1
        pair_completed = reference_status == "completed" and mutant_status == "completed"
        delta = None
        if pair_completed and reference_energy is not None and mutant_energy is not None:
            delta = float(mutant_energy) - float(reference_energy)
        rows.append(
            {
                "gene": row.get("gene"),
                "hgvs_p": hgvs_p,
                "model_request_id": model_id,
                "aa_ref": parsed.get("aa_ref"),
                "position": position,
                "aa_alt": alt,
                "mutation_coordinate_status": mutation_status,
                "coordinate_review_status": "draft_needs_rotamer_protonation_and_domain_review",
                "reference_pair_pdb_path": str(reference_pair_pdb) if reference_pair_pdb.exists() else "",
                "reference_pair_xyz_path": str(reference_pair_xyz) if reference_pair_xyz.exists() else "",
                "draft_mutant_fragment_pdb_path": str(mutant_pdb) if mutant_pdb.exists() else "",
                "draft_mutant_fragment_xyz_path": str(mutant_xyz) if mutant_xyz.exists() else "",
                "reference_xtb_status": reference_status,
                "draft_mutant_xtb_status": mutant_status,
                "reference_total_energy_hartree": reference_energy,
                "draft_mutant_total_energy_hartree": mutant_energy,
                "delta_mutant_minus_reference_hartree": delta,
                "paired_status": "paired_xtb_completed" if pair_completed else ("coordinates_prepared" if mutation_status == "draft_sidechain_substitution" else mutation_status),
                "interpretation_guardrail": "draft neutral heavy-atom xTB screen; not publication-grade mutant structure",
            }
        )
    pair_table = pd.DataFrame(rows)
    xtb_table = pd.DataFrame(xtb_logs)
    draft_count = int(pair_table["mutation_coordinate_status"].eq("draft_sidechain_substitution").sum()) if not pair_table.empty else 0
    paired_completed = int(pair_table["paired_status"].eq("paired_xtb_completed").sum()) if not pair_table.empty else 0
    target_count = int(payload["summary_seed"]["target_count"])
    coordinate_component = (draft_count / max(target_count, 1)) * 55
    paired_component = (paired_completed / max(attempted_pairs, 1)) * 35 if attempted_pairs else 0
    engine_component = 10 if xtb_path else 0
    readiness = _percent(coordinate_component + paired_component + engine_component)
    mean_delta = None
    if "delta_mutant_minus_reference_hartree" in pair_table.columns:
        deltas = pd.to_numeric(pair_table["delta_mutant_minus_reference_hartree"], errors="coerce").dropna()
        mean_delta = float(deltas.mean()) if not deltas.empty else None
    summary = {
        **payload["summary_seed"],
        "xtb_available": bool(xtb_path),
        "draft_mutant_coordinate_count": draft_count,
        "paired_xtb_attempted_count": attempted_pairs,
        "paired_xtb_completed_count": paired_completed,
        "mean_delta_mutant_minus_reference_hartree": mean_delta,
        "paired_mutant_execution_readiness_percent": readiness,
        "ready_for_publication_grade_mutant_effect_claims": False,
        "why_not_publication_grade": "Draft side-chain substitutions need rotamer/protonation review, paired optimized geometries, and orthogonal functional or biophysical confirmation.",
    }
    markdown = _build_markdown(summary)
    pair_table_path = output_root / "brca1_paired_mutant_xtb_table.csv"
    xtb_log_path = output_root / "brca1_paired_mutant_xtb_execution_log.csv"
    manifest_path = output_root / "brca1_paired_mutant_execution_manifest.json"
    markdown_path = output_root / "brca1_paired_mutant_execution_report.md"
    html_path = output_root / "brca1_paired_mutant_execution_report.html"
    pair_table.to_csv(pair_table_path, index=False)
    xtb_table.to_csv(xtb_log_path, index=False)
    markdown_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(_render_markdown_html(markdown, "PrimeVarClass BRCA1 Paired Mutant Execution"), encoding="utf-8")
    manifest = {
        "generated_at": _now_utc(),
        "summary": summary,
        "paired_mutant_table_path": str(pair_table_path),
        "paired_mutant_xtb_execution_log_path": str(xtb_log_path),
        "paired_mutant_fragments_dir": str(pairs_dir),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
    }
    manifest_path.write_text(json.dumps(_jsonify(manifest), indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "brca1_paired_mutant_execution": {
            "summary": summary,
            "paired_mutant_table": pair_table,
            "paired_mutant_xtb_execution_log": xtb_table,
        },
        "brca1_paired_mutant_execution_manifest_path": str(manifest_path),
        "brca1_paired_mutant_table_path": str(pair_table_path),
        "brca1_paired_mutant_xtb_execution_log_path": str(xtb_log_path),
        "brca1_paired_mutant_fragments_dir": str(pairs_dir),
        "brca1_paired_mutant_execution_report_markdown_path": str(markdown_path),
        "brca1_paired_mutant_execution_report_html_path": str(html_path),
    }
