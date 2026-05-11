from __future__ import annotations

import json
import math
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .brca1_engine_execution import _engine_paths
from .real_data_preparation import _jsonify, _render_markdown_html


HGVS_RE = re.compile(r"^p\.([A-Za-z]{3})(\d+)([A-Za-z]{3})$")


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


def _parse_hgvs_p(hgvs_p: str) -> dict[str, Any]:
    match = HGVS_RE.match(str(hgvs_p or "").strip())
    if not match:
        return {"aa_ref": "", "position": None, "aa_alt": ""}
    return {"aa_ref": match.group(1), "position": int(match.group(2)), "aa_alt": match.group(3)}


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


def _parse_pdb_atoms(pdb_path: str | Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    path = Path(pdb_path)
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.startswith(("ATOM  ", "HETATM")):
            continue
        try:
            rows.append(
                {
                    "record": line[0:6].strip(),
                    "serial": int(line[6:11]),
                    "atom_name": line[12:16].strip(),
                    "alt_loc": line[16:17].strip(),
                    "res_name": line[17:20].strip(),
                    "chain_id": line[21:22].strip() or "A",
                    "resseq": int(line[22:26]),
                    "icode": line[26:27].strip(),
                    "x": float(line[30:38]),
                    "y": float(line[38:46]),
                    "z": float(line[46:54]),
                    "occupancy": float(line[54:60] or 0),
                    "plddt": float(line[60:66] or 0),
                    "element": (line[76:78].strip() or line[12:16].strip()[0]).title(),
                }
            )
        except Exception:
            continue
    return pd.DataFrame(rows)


def _distance(a: pd.Series, b: pd.Series) -> float:
    return math.sqrt((float(a["x"]) - float(b["x"])) ** 2 + (float(a["y"]) - float(b["y"])) ** 2 + (float(a["z"]) - float(b["z"])) ** 2)


def _select_fragment_atoms(atoms: pd.DataFrame, position: int, radius_angstrom: float, max_atoms: int) -> pd.DataFrame:
    if atoms.empty:
        return pd.DataFrame()
    protein_atoms = atoms.loc[atoms["record"].eq("ATOM")].copy()
    target = protein_atoms.loc[protein_atoms["resseq"].eq(position)]
    if target.empty:
        return pd.DataFrame()
    target_coords = target[["x", "y", "z"]].to_numpy(dtype=float)
    residue_keys: set[tuple[str, int, str]] = set()
    for _, row in protein_atoms.iterrows():
        coords = np.array([row["x"], row["y"], row["z"]], dtype=float)
        min_distance = float(np.sqrt(((target_coords - coords) ** 2).sum(axis=1)).min())
        if min_distance <= radius_angstrom:
            residue_keys.add((str(row["chain_id"]), int(row["resseq"]), str(row["icode"])))
    fragment = protein_atoms.loc[
        protein_atoms.apply(lambda row: (str(row["chain_id"]), int(row["resseq"]), str(row["icode"])) in residue_keys, axis=1)
    ].copy()
    if len(fragment) > max_atoms:
        target_center = target[["x", "y", "z"]].astype(float).mean().to_numpy()
        fragment["distance_to_target"] = fragment.apply(
            lambda row: float(np.sqrt(((np.array([row["x"], row["y"], row["z"]], dtype=float) - target_center) ** 2).sum())),
            axis=1,
        )
        keep_residues = (
            fragment.groupby(["chain_id", "resseq", "icode"], dropna=False)["distance_to_target"]
            .min()
            .reset_index()
            .sort_values("distance_to_target")
        )
        selected: set[tuple[str, int, str]] = set()
        atom_count = 0
        for _, residue in keep_residues.iterrows():
            key = (str(residue["chain_id"]), int(residue["resseq"]), str(residue["icode"]))
            count = int(((fragment["chain_id"].astype(str) == key[0]) & (fragment["resseq"].astype(int) == key[1]) & (fragment["icode"].astype(str) == key[2])).sum())
            if selected and atom_count + count > max_atoms:
                continue
            selected.add(key)
            atom_count += count
            if atom_count >= max_atoms:
                break
        fragment = fragment.loc[
            fragment.apply(lambda row: (str(row["chain_id"]), int(row["resseq"]), str(row["icode"])) in selected, axis=1)
        ].copy()
    return fragment.sort_values(["chain_id", "resseq", "serial"], kind="stable")


def _write_pdb(atoms: pd.DataFrame, path: Path) -> None:
    lines: list[str] = []
    for idx, row in enumerate(atoms.to_dict(orient="records"), start=1):
        lines.append(
            f"ATOM  {idx:5d} {str(row['atom_name'])[:4]:>4s} {str(row['res_name'])[:3]:>3s} {str(row['chain_id'] or 'A')[:1]:1s}"
            f"{int(row['resseq']):4d}{str(row.get('icode') or ' ')[:1]:1s}   "
            f"{float(row['x']):8.3f}{float(row['y']):8.3f}{float(row['z']):8.3f}"
            f"{float(row.get('occupancy') or 1):6.2f}{float(row.get('plddt') or 0):6.2f}          {str(row['element'])[:2]:>2s}"
        )
    lines.append("END")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_xyz(atoms: pd.DataFrame, path: Path, comment: str) -> None:
    lines = [str(len(atoms)), comment]
    for row in atoms.to_dict(orient="records"):
        lines.append(f"{str(row['element'])[:2]:2s} {float(row['x']): .6f} {float(row['y']): .6f} {float(row['z']): .6f}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run_xtb(xtb_path: str, xyz_path: Path, work_dir: Path, timeout_sec: int) -> dict[str, Any]:
    command = [xtb_path, str(xyz_path), "--gfn", "2", "--sp", "--chrg", "0"]
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
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        energy = None
        for line in stdout.splitlines():
            if "TOTAL ENERGY" in line.upper():
                values = re.findall(r"[-+]?\d+\.\d+", line)
                if values:
                    energy = float(values[-1])
        return {
            "started_at": started_at,
            "finished_at": _now_utc(),
            "command": " ".join(command),
            "status": "completed" if completed.returncode == 0 else "failed",
            "return_code": completed.returncode,
            "total_energy_hartree": energy,
            "stdout_tail": stdout[-2000:],
            "stderr_tail": stderr[-2000:],
        }
    except Exception as exc:
        return {
            "started_at": started_at,
            "finished_at": _now_utc(),
            "command": " ".join(command),
            "status": "failed",
            "return_code": -1,
            "total_energy_hartree": None,
            "stdout_tail": "",
            "stderr_tail": str(exc),
        }


def _build_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# PrimeVarClass BRCA1 Fragment Preparation",
        "",
        f"- Generated at: `{summary.get('generated_at')}`",
        f"- Targets requested: `{summary.get('target_count')}`",
        f"- Prepared reference fragments: `{summary.get('prepared_fragment_count')}`",
        f"- xTB attempted fragments: `{summary.get('xtb_attempted_count')}`",
        f"- xTB completed fragments: `{summary.get('xtb_completed_count')}`",
        f"- Preparation readiness: `{summary.get('fragment_preparation_readiness_percent')}%`",
        "",
        "## Scientific boundary",
        "",
        "- These fragments are real AlphaFold-derived reference local environments.",
        "- They are not yet validated mutant side-chain models.",
        "- Executed xTB results are baseline physical checks until reviewed mutant coordinates are generated.",
    ]
    return "\n".join(lines).strip()


def build_brca1_fragment_preparation_package(
    *,
    brca1_engine_execution_manifest_path: str,
    radius_angstrom: float = 5.0,
    max_atoms: int = 90,
    execute_xtb: bool = True,
    max_xtb_runs: int = 2,
    xtb_timeout_sec: int = 240,
) -> dict[str, Any]:
    manifest = json.loads(Path(brca1_engine_execution_manifest_path).read_text(encoding="utf-8"))
    queue = _read_table(manifest.get("input_preparation_queue_path") or manifest.get("execution_queue_path"))
    reference_paths = manifest.get("reference_structure_paths") or {}
    pdb_path = reference_paths.get("pdb_path")
    atoms = _parse_pdb_atoms(pdb_path) if pdb_path else pd.DataFrame()
    engine_paths = manifest.get("engine_paths") or _engine_paths()
    xtb_path = engine_paths.get("xtb", "")

    prepared_rows: list[dict[str, Any]] = []
    xtb_rows: list[dict[str, Any]] = []
    output_hint_rows: list[dict[str, Any]] = []
    for _, row in queue.iterrows():
        hgvs_p = str(row.get("hgvs_p") or "")
        parsed = _parse_hgvs_p(hgvs_p)
        position = parsed.get("position")
        if not position:
            continue
        fragment = _select_fragment_atoms(atoms, int(position), radius_angstrom, max_atoms)
        status = "prepared_reference_fragment" if not fragment.empty else "missing_reference_residue"
        prepared_rows.append(
            {
                "gene": row.get("gene"),
                "hgvs_p": hgvs_p,
                "model_request_id": row.get("model_request_id"),
                "aa_ref": parsed.get("aa_ref"),
                "position": position,
                "aa_alt": parsed.get("aa_alt"),
                "fragment_atom_count": int(len(fragment)),
                "fragment_residue_count": int(fragment[["chain_id", "resseq", "icode"]].drop_duplicates().shape[0]) if not fragment.empty else 0,
                "mean_fragment_plddt": round(float(fragment["plddt"].mean()), 3) if not fragment.empty else None,
                "preparation_status": status,
                "scientific_scope": "AlphaFold reference local environment; mutant side-chain not yet modeled",
            }
        )
        if fragment.empty:
            continue
        output_hint_rows.append({"model_request_id": row.get("model_request_id"), "fragment": fragment})
    return {
        "summary_seed": {
            "generated_at": _now_utc(),
            "target_count": int(len(queue)),
            "reference_pdb_path": pdb_path,
            "radius_angstrom": radius_angstrom,
            "max_atoms": max_atoms,
            "xtb_available": bool(xtb_path),
        },
        "prepared_rows": prepared_rows,
        "fragments": output_hint_rows,
        "xtb_rows": xtb_rows,
        "engine_paths": engine_paths,
        "execute_xtb": execute_xtb,
        "max_xtb_runs": max_xtb_runs,
        "xtb_timeout_sec": xtb_timeout_sec,
    }


def export_brca1_fragment_preparation_package(
    *,
    brca1_engine_execution_manifest_path: str,
    output_dir: str,
    radius_angstrom: float = 5.0,
    max_atoms: int = 90,
    execute_xtb: bool = True,
    max_xtb_runs: int = 2,
    xtb_timeout_sec: int = 240,
) -> dict[str, Any]:
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    payload = build_brca1_fragment_preparation_package(
        brca1_engine_execution_manifest_path=brca1_engine_execution_manifest_path,
        radius_angstrom=radius_angstrom,
        max_atoms=max_atoms,
        execute_xtb=execute_xtb,
        max_xtb_runs=max_xtb_runs,
        xtb_timeout_sec=xtb_timeout_sec,
    )
    fragments_dir = output_root / "prepared_fragments"
    fragments_dir.mkdir(parents=True, exist_ok=True)
    prepared_rows = payload["prepared_rows"]
    xtb_rows: list[dict[str, Any]] = []
    xtb_runs = 0
    xtb_path = payload["engine_paths"].get("xtb", "")
    for item in payload["fragments"]:
        model_id = str(item["model_request_id"])
        fragment = item["fragment"]
        model_dir = fragments_dir / model_id
        model_dir.mkdir(parents=True, exist_ok=True)
        pdb_path = model_dir / f"{model_id}.reference_fragment.pdb"
        xyz_path = model_dir / f"{model_id}.reference_fragment.xyz"
        _write_pdb(fragment, pdb_path)
        _write_xyz(fragment, xyz_path, f"{model_id} AlphaFold reference fragment")
        for row in prepared_rows:
            if str(row.get("model_request_id")) == model_id:
                row["reference_fragment_pdb_path"] = str(pdb_path)
                row["reference_fragment_xyz_path"] = str(xyz_path)
                row["xtb_baseline_status"] = "not_attempted"
        if execute_xtb and xtb_path and xtb_runs < max_xtb_runs:
            result = _run_xtb(xtb_path, xyz_path, model_dir, timeout_sec=xtb_timeout_sec)
            result.update({"model_request_id": model_id, "reference_fragment_xyz_path": str(xyz_path)})
            xtb_rows.append(result)
            xtb_runs += 1
            for row in prepared_rows:
                if str(row.get("model_request_id")) == model_id:
                    row["xtb_baseline_status"] = result["status"]
                    row["xtb_total_energy_hartree"] = result.get("total_energy_hartree")

    prepared_table = pd.DataFrame(prepared_rows)
    xtb_table = pd.DataFrame(xtb_rows)
    prepared_count = int(prepared_table["preparation_status"].eq("prepared_reference_fragment").sum()) if not prepared_table.empty else 0
    xtb_completed = int(xtb_table["status"].eq("completed").sum()) if not xtb_table.empty else 0
    target_count = int(payload["summary_seed"]["target_count"])
    preparation_component = (prepared_count / target_count) * 70 if target_count else 0
    xtb_component = (xtb_completed / max(int(len(xtb_table)), 1)) * 30 if not xtb_table.empty else 0
    readiness = _percent(preparation_component + xtb_component)
    summary = {
        **payload["summary_seed"],
        "prepared_fragment_count": prepared_count,
        "xtb_attempted_count": int(len(xtb_table)),
        "xtb_completed_count": xtb_completed,
        "fragment_preparation_readiness_percent": readiness,
        "ready_for_mutant_effect_claims": False,
        "why_not_mutant_effect_claims": "Reference fragments are prepared; reviewed mutant side-chain coordinates and paired reference-vs-mutant execution are still required.",
    }
    markdown = _build_markdown(summary)
    prepared_path = output_root / "brca1_prepared_fragment_table.csv"
    xtb_path_out = output_root / "brca1_xtb_baseline_execution_log.csv"
    manifest_path = output_root / "brca1_fragment_preparation_manifest.json"
    markdown_path = output_root / "brca1_fragment_preparation_report.md"
    html_path = output_root / "brca1_fragment_preparation_report.html"
    prepared_table.to_csv(prepared_path, index=False)
    xtb_table.to_csv(xtb_path_out, index=False)
    markdown_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(_render_markdown_html(markdown, "PrimeVarClass BRCA1 Fragment Preparation"), encoding="utf-8")
    manifest = {
        "generated_at": _now_utc(),
        "summary": summary,
        "prepared_fragment_table_path": str(prepared_path),
        "xtb_baseline_execution_log_path": str(xtb_path_out),
        "prepared_fragments_dir": str(fragments_dir),
        "engine_paths": payload.get("engine_paths") or {},
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
    }
    manifest_path.write_text(json.dumps(_jsonify(manifest), indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "brca1_fragment_preparation": {
            "summary": summary,
            "prepared_fragment_table": prepared_table,
            "xtb_baseline_execution_log": xtb_table,
        },
        "brca1_fragment_preparation_manifest_path": str(manifest_path),
        "brca1_prepared_fragment_table_path": str(prepared_path),
        "brca1_xtb_baseline_execution_log_path": str(xtb_path_out),
        "brca1_prepared_fragments_dir": str(fragments_dir),
        "brca1_fragment_preparation_report_markdown_path": str(markdown_path),
        "brca1_fragment_preparation_report_html_path": str(html_path),
    }
