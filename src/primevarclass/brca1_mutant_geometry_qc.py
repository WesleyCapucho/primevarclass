from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .brca1_engine_execution import _engine_paths
from .brca1_fragment_preparation import _parse_pdb_atoms
from .real_data_preparation import _jsonify, _render_markdown_html


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


def _min_distance_and_clashes(atoms: pd.DataFrame) -> tuple[float | None, int]:
    if atoms.empty:
        return None, 0
    coords = atoms[["x", "y", "z"]].to_numpy(dtype=float)
    min_distance: float | None = None
    clash_count = 0
    residue_ids = atoms[["chain_id", "resseq", "atom_name"]].astype(str).agg(":".join, axis=1).tolist()
    for i, j in combinations(range(len(coords)), 2):
        if residue_ids[i].rsplit(":", 1)[0] == residue_ids[j].rsplit(":", 1)[0]:
            continue
        distance = float(np.linalg.norm(coords[i] - coords[j]))
        min_distance = distance if min_distance is None else min(min_distance, distance)
        if distance < 1.0:
            clash_count += 1
    return min_distance, clash_count


def _read_xyz_energy(path: Path) -> float | None:
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    for line in text.splitlines()[:5]:
        if "energy:" in line.lower():
            match = re.search(r"energy:\s*([-+]?\d+(?:\.\d+)?)", line, flags=re.IGNORECASE)
            if match:
                return float(match.group(1))
    return None


def _run_xtb_opt(xtb_path: str, xyz_path: Path, work_dir: Path, timeout_sec: int) -> dict[str, Any]:
    command = [xtb_path, str(xyz_path), "--gfn", "2", "--opt", "loose", "--chrg", "0"]
    started_at = _now_utc()
    try:
        completed = subprocess.run(
            command,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
        )
        xtbopt = work_dir / "xtbopt.xyz"
        optimized_energy = _read_xyz_energy(xtbopt)
        return {
            "started_at": started_at,
            "finished_at": _now_utc(),
            "command": " ".join(command),
            "status": "completed" if completed.returncode == 0 and xtbopt.exists() else "failed",
            "return_code": completed.returncode,
            "optimized_xyz_path": str(xtbopt) if xtbopt.exists() else "",
            "optimized_energy_hartree": optimized_energy,
            "stdout_tail": (completed.stdout or "")[-2000:],
            "stderr_tail": (completed.stderr or "")[-2000:],
        }
    except Exception as exc:
        return {
            "started_at": started_at,
            "finished_at": _now_utc(),
            "command": " ".join(command),
            "status": "failed",
            "return_code": -1,
            "optimized_xyz_path": "",
            "optimized_energy_hartree": None,
            "stdout_tail": "",
            "stderr_tail": str(exc),
        }


def _build_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# PrimeVarClass BRCA1 Mutant Geometry QC",
        "",
        f"- Generated at: `{summary.get('generated_at')}`",
        f"- Mutant pairs reviewed: `{summary.get('reviewed_pair_count')}`",
        f"- Geometry-pass pairs: `{summary.get('geometry_pass_count')}`",
        f"- xTB optimizations attempted: `{summary.get('xtb_optimization_attempted_count')}`",
        f"- xTB optimizations completed: `{summary.get('xtb_optimization_completed_count')}`",
        f"- Geometry QC readiness: `{summary.get('mutant_geometry_qc_readiness_percent')}%`",
        "",
        "## Scientific boundary",
        "",
        "- This package checks heavy-atom geometry and optional xTB loose optimization.",
        "- It does not replace rotamer, protonation, domain-context, MD, DFT, docking, or wet-lab review.",
    ]
    return "\n".join(lines).strip()


def build_brca1_mutant_geometry_qc_package(
    *,
    brca1_paired_mutant_execution_manifest_path: str,
    execute_xtb_opt: bool = True,
    max_opt_pairs: int = 2,
    xtb_timeout_sec: int = 360,
) -> dict[str, Any]:
    manifest = json.loads(Path(brca1_paired_mutant_execution_manifest_path).read_text(encoding="utf-8"))
    paired_table = _read_table(manifest.get("paired_mutant_table_path"))
    engine_paths = manifest.get("engine_paths") or _engine_paths()
    return {
        "summary_seed": {
            "generated_at": _now_utc(),
            "source_paired_mutant_manifest_path": str(Path(brca1_paired_mutant_execution_manifest_path).expanduser().resolve()),
            "paired_row_count": int(len(paired_table)),
            "execute_xtb_opt": bool(execute_xtb_opt),
            "max_opt_pairs": int(max_opt_pairs),
            "xtb_timeout_sec": int(xtb_timeout_sec),
        },
        "paired_table": paired_table,
        "engine_paths": engine_paths,
        "execute_xtb_opt": bool(execute_xtb_opt),
        "max_opt_pairs": int(max_opt_pairs),
        "xtb_timeout_sec": int(xtb_timeout_sec),
    }


def export_brca1_mutant_geometry_qc_package(
    *,
    brca1_paired_mutant_execution_manifest_path: str,
    output_dir: str,
    execute_xtb_opt: bool = True,
    max_opt_pairs: int = 2,
    xtb_timeout_sec: int = 360,
) -> dict[str, Any]:
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    payload = build_brca1_mutant_geometry_qc_package(
        brca1_paired_mutant_execution_manifest_path=brca1_paired_mutant_execution_manifest_path,
        execute_xtb_opt=execute_xtb_opt,
        max_opt_pairs=max_opt_pairs,
        xtb_timeout_sec=xtb_timeout_sec,
    )
    xtb_path = str(payload["engine_paths"].get("xtb") or "")
    rows: list[dict[str, Any]] = []
    opt_rows: list[dict[str, Any]] = []
    opt_runs = 0
    for _, row in payload["paired_table"].iterrows():
        mutant_path = Path(str(row.get("draft_mutant_fragment_pdb_path") or ""))
        reference_path = Path(str(row.get("reference_pair_pdb_path") or ""))
        mutant_atoms = _parse_pdb_atoms(mutant_path) if mutant_path.exists() else pd.DataFrame()
        reference_atoms = _parse_pdb_atoms(reference_path) if reference_path.exists() else pd.DataFrame()
        mutant_min_distance, mutant_clashes = _min_distance_and_clashes(mutant_atoms)
        reference_min_distance, reference_clashes = _min_distance_and_clashes(reference_atoms)
        geometry_pass = bool(mutant_atoms.shape[0] > 0 and mutant_clashes == 0 and (mutant_min_distance is None or mutant_min_distance >= 1.0))
        opt_status = "not_attempted"
        opt_energy = None
        optimized_xyz = ""
        mutant_xyz = Path(str(row.get("draft_mutant_fragment_xyz_path") or ""))
        if payload["execute_xtb_opt"] and xtb_path and mutant_xyz.exists() and opt_runs < int(payload["max_opt_pairs"]):
            work_dir = output_root / "xtb_optimized_mutants" / str(row.get("model_request_id") or f"pair_{opt_runs+1}")
            work_dir.mkdir(parents=True, exist_ok=True)
            local_xyz = work_dir / mutant_xyz.name
            local_xyz.write_text(mutant_xyz.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
            result = _run_xtb_opt(xtb_path, local_xyz, work_dir, int(payload["xtb_timeout_sec"]))
            result.update({"model_request_id": row.get("model_request_id"), "hgvs_p": row.get("hgvs_p")})
            opt_rows.append(result)
            opt_status = str(result.get("status") or "")
            opt_energy = result.get("optimized_energy_hartree")
            optimized_xyz = str(result.get("optimized_xyz_path") or "")
            opt_runs += 1
        rows.append(
            {
                "gene": row.get("gene"),
                "hgvs_p": row.get("hgvs_p"),
                "model_request_id": row.get("model_request_id"),
                "paired_status": row.get("paired_status"),
                "coordinate_review_status": row.get("coordinate_review_status"),
                "reference_min_inter_residue_distance_angstrom": reference_min_distance,
                "reference_clash_count": reference_clashes,
                "mutant_min_inter_residue_distance_angstrom": mutant_min_distance,
                "mutant_clash_count": mutant_clashes,
                "geometry_qc_status": "geometry_pass" if geometry_pass else "needs_rotamer_or_coordinate_review",
                "xtb_optimization_status": opt_status,
                "xtb_optimized_energy_hartree": opt_energy,
                "xtb_optimized_xyz_path": optimized_xyz,
                "publication_grade_status": "not_publication_grade_needs_expert_review",
            }
        )
    qc_table = pd.DataFrame(rows)
    opt_table = pd.DataFrame(opt_rows)
    reviewed_count = int(len(qc_table))
    geometry_pass_count = int(qc_table["geometry_qc_status"].eq("geometry_pass").sum()) if not qc_table.empty else 0
    opt_completed = int(opt_table["status"].eq("completed").sum()) if not opt_table.empty else 0
    geometry_component = (geometry_pass_count / max(reviewed_count, 1)) * 55
    optimization_component = (opt_completed / max(int(len(opt_table)), 1)) * 30 if not opt_table.empty else 0
    engine_component = 15 if xtb_path else 0
    readiness = _percent(geometry_component + optimization_component + engine_component)
    summary = {
        **payload["summary_seed"],
        "xtb_available": bool(xtb_path),
        "reviewed_pair_count": reviewed_count,
        "geometry_pass_count": geometry_pass_count,
        "xtb_optimization_attempted_count": int(len(opt_table)),
        "xtb_optimization_completed_count": opt_completed,
        "mutant_geometry_qc_readiness_percent": readiness,
        "ready_for_reviewed_mutant_structure_claims": False,
        "why_not_reviewed_structure_claims": "Automated geometry QC and loose xTB optimization still require expert rotamer/protonation review, domain context, and orthogonal experimental/biophysical evidence.",
    }
    markdown = _build_markdown(summary)
    qc_path = output_root / "brca1_mutant_geometry_qc_table.csv"
    opt_path = output_root / "brca1_xtb_optimization_log.csv"
    manifest_path = output_root / "brca1_mutant_geometry_qc_manifest.json"
    markdown_path = output_root / "brca1_mutant_geometry_qc_report.md"
    html_path = output_root / "brca1_mutant_geometry_qc_report.html"
    qc_table.to_csv(qc_path, index=False)
    opt_table.to_csv(opt_path, index=False)
    markdown_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(_render_markdown_html(markdown, "PrimeVarClass BRCA1 Mutant Geometry QC"), encoding="utf-8")
    manifest = {
        "generated_at": _now_utc(),
        "summary": summary,
        "mutant_geometry_qc_table_path": str(qc_path),
        "xtb_optimization_log_path": str(opt_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
    }
    manifest_path.write_text(json.dumps(_jsonify(manifest), indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "brca1_mutant_geometry_qc": {
            "summary": summary,
            "mutant_geometry_qc_table": qc_table,
            "xtb_optimization_log": opt_table,
        },
        "brca1_mutant_geometry_qc_manifest_path": str(manifest_path),
        "brca1_mutant_geometry_qc_table_path": str(qc_path),
        "brca1_xtb_optimization_log_path": str(opt_path),
        "brca1_mutant_geometry_qc_report_markdown_path": str(markdown_path),
        "brca1_mutant_geometry_qc_report_html_path": str(html_path),
    }
