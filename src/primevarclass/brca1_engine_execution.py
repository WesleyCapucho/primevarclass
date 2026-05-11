from __future__ import annotations

import importlib.util
import csv
import os
import json
import shutil
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .real_data_preparation import _jsonify, _render_markdown_html


ALPHAFOLD_API_URL = "https://alphafold.ebi.ac.uk/api/prediction/{uniprot_id}"
BRCA1_UNIPROT_ID = "P38398"
DEFAULT_STRUCTURAL_ENGINE_PREFIX = Path(r"C:\primevarclass_mamba\envs\primevarclass-structural-engines")


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


def _load_json(path_value: str | None) -> dict[str, Any]:
    if not path_value:
        return {}
    path = Path(path_value).expanduser()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _read_table(path_value: str | None) -> pd.DataFrame:
    if not path_value:
        return pd.DataFrame()
    path = Path(path_value).expanduser()
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def _candidate_engine_prefixes() -> list[Path]:
    prefixes: list[Path] = []
    env_prefix = os.environ.get("PRIMEVARCLASS_STRUCTURAL_ENGINE_PREFIX")
    if env_prefix:
        prefixes.append(Path(env_prefix))
    prefixes.append(DEFAULT_STRUCTURAL_ENGINE_PREFIX)
    return [prefix for prefix in prefixes if prefix.exists()]


def _find_executable(names: list[str]) -> str:
    for name in names:
        resolved = shutil.which(name)
        if resolved:
            return resolved
    suffixes = [".exe", ""]
    subdirs = ["Library/bin", "Scripts", "bin"]
    for prefix in _candidate_engine_prefixes():
        for subdir in subdirs:
            for name in names:
                for suffix in suffixes:
                    candidate = prefix / subdir / f"{name}{suffix}"
                    if candidate.exists():
                        return str(candidate)
    return ""


def _engine_paths() -> dict[str, str]:
    return {
        "xtb": _find_executable(["xtb"]),
        "psi4": _find_executable(["psi4"]),
        "vina": _find_executable(["vina", "autodock_vina", "qvina2", "qvina"]),
        "obabel": _find_executable(["obabel"]),
    }


def _engine_status() -> dict[str, bool]:
    paths = _engine_paths()
    return {
        "xtb": bool(paths.get("xtb")),
        "psi4": bool(paths.get("psi4")),
        "vina": bool(paths.get("vina")),
        "obabel": bool(paths.get("obabel")),
        "openmm": importlib.util.find_spec("openmm") is not None,
        "qiskit_nature": importlib.util.find_spec("qiskit_nature") is not None,
    }


def _engine_diagnostics(engine_state: dict[str, bool], engine_paths: dict[str, str]) -> pd.DataFrame:
    rows = [
        {
            "engine": "xtb",
            "available": bool(engine_state.get("xtb")),
            "resolved_path": engine_paths.get("xtb", ""),
            "detector": "PATH executable: xtb",
            "required_for": "semiempirical geometry/energy triage",
            "install_hint": "Install from conda-forge in the provided environment.structural-engines.yml.",
            "claim_unlocked": "Executed xTB structural/energetic evidence",
        },
        {
            "engine": "psi4",
            "available": bool(engine_state.get("psi4")),
            "resolved_path": engine_paths.get("psi4", ""),
            "detector": "PATH executable: psi4",
            "required_for": "DFT fragment confirmation",
            "install_hint": "Install from conda-forge in the provided environment.structural-engines.yml.",
            "claim_unlocked": "Executed DFT fragment evidence",
        },
        {
            "engine": "openmm",
            "available": bool(engine_state.get("openmm")),
            "resolved_path": "python module: openmm" if engine_state.get("openmm") else "",
            "detector": "Python module: openmm",
            "required_for": "molecular mechanics relaxation and mutation-local context",
            "install_hint": "Install openmm and pdbfixer from conda-forge.",
            "claim_unlocked": "Executed molecular-mechanics relaxation evidence",
        },
        {
            "engine": "vina",
            "available": bool(engine_state.get("vina")),
            "resolved_path": engine_paths.get("vina", ""),
            "detector": "PATH executable: vina, autodock_vina, qvina2, or qvina",
            "required_for": "ligand/docking vulnerability screening",
            "install_hint": "Install vina from conda-forge.",
            "claim_unlocked": "Executed docking evidence",
        },
        {
            "engine": "obabel",
            "available": bool(engine_state.get("obabel")),
            "resolved_path": engine_paths.get("obabel", ""),
            "detector": "PATH executable: obabel",
            "required_for": "ligand/protein file conversion",
            "install_hint": "Install openbabel from conda-forge.",
            "claim_unlocked": "Reproducible ligand/protein format conversion",
        },
        {
            "engine": "qiskit_nature",
            "available": bool(engine_state.get("qiskit_nature")),
            "resolved_path": "python module: qiskit_nature" if engine_state.get("qiskit_nature") else "",
            "detector": "Python module: qiskit_nature",
            "required_for": "prime-guided VQE electronic-structure experiments",
            "install_hint": "Install qiskit-nature and qiskit-algorithms with pip in the structural environment.",
            "claim_unlocked": "Executed prime-guided VQE evidence",
        },
    ]
    diagnostics = pd.DataFrame(rows)
    diagnostics["status"] = np.where(diagnostics["available"], "available", "missing")
    diagnostics["blocks_executed_claims"] = ~diagnostics["available"]
    return diagnostics


def _fetch_alphafold_metadata(uniprot_id: str, timeout_sec: int) -> dict[str, Any]:
    url = ALPHAFOLD_API_URL.format(uniprot_id=uniprot_id)
    try:
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            records = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {"status": "error", "url": url, "error": str(exc), "records": []}
    compact_records = []
    for record in records if isinstance(records, list) else []:
        compact_records.append(
            {
                "entry_id": record.get("entryId"),
                "gene": record.get("gene"),
                "uniprot_accession": record.get("uniprotAccession"),
                "uniprot_id": record.get("uniprotId"),
                "model_created_date": record.get("modelCreatedDate"),
                "latest_version": record.get("latestVersion"),
                "sequence_version_date": record.get("sequenceVersionDate"),
                "cif_url": record.get("cifUrl"),
                "pdb_url": record.get("pdbUrl"),
                "pae_doc_url": record.get("paeDocUrl"),
                "plddt_doc_url": record.get("plddtDocUrl"),
            }
        )
    return {
        "status": "found" if compact_records else "not_found",
        "url": url,
        "record_count": len(compact_records),
        "records": compact_records,
    }


def _quote_path(path_value: Any) -> str:
    text = str(path_value or "").strip()
    return f'"{text}"' if text else ""


def _command_for_template(engine: str, template_path: Any, engine_paths: dict[str, str] | None = None) -> str:
    path = str(template_path or "").strip()
    if not path or path.lower() == "nan":
        return ""
    paths = engine_paths or {}
    if engine == "xtb":
        executable = paths.get("xtb") or "xtb"
        return f"{_quote_path(executable)} {_quote_path(path)}"
    if engine == "psi4":
        executable = paths.get("psi4") or "psi4"
        return f"{_quote_path(executable)} {_quote_path(path)}"
    if engine == "openmm":
        return f"python {_quote_path(path)}"
    if engine == "vina":
        executable = paths.get("vina") or "vina"
        return f"{_quote_path(executable)} --config {_quote_path(path)}"
    if engine == "qiskit_nature":
        return f"python {_quote_path(path)}"
    return ""


def _template_input_blockers(*template_paths: Any) -> list[str]:
    blockers: list[str] = []
    patterns = [
        ("placeholder_coordinates", "placeholder coordinates"),
        ("paste_qm_fragment_coordinates", "paste qm fragment coordinates"),
        ("todo_marker", "todo:"),
        ("mutant_fragment_placeholder", "mutant_fragment.xyz"),
        ("prepared_pdb_placeholder", "mutant_prepared.pdb"),
        ("fill_fragment_geometry", "fill fragment geometry"),
    ]
    for template_path in template_paths:
        path_text = str(template_path or "").strip()
        if not path_text or path_text.lower() == "nan":
            continue
        path = Path(path_text)
        if not path.exists():
            blockers.append(f"missing_template:{path.name}")
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore").lower()
        except Exception:
            blockers.append(f"unreadable_template:{path.name}")
            continue
        for blocker_id, pattern in patterns:
            if pattern in content:
                blockers.append(f"{blocker_id}:{path.name}")
    return sorted(set(blockers))


def _build_execution_queue(
    campaign_table: pd.DataFrame,
    engine_state: dict[str, bool],
    engine_paths: dict[str, str],
    alphafold_metadata: dict[str, Any],
) -> pd.DataFrame:
    if campaign_table.empty:
        return pd.DataFrame()
    reference_record = (alphafold_metadata.get("records") or [{}])[0] if alphafold_metadata.get("records") else {}
    rows: list[dict[str, Any]] = []
    for _, row in campaign_table.iterrows():
        xtb_command = _command_for_template("xtb", row.get("xtb_template_path"), engine_paths)
        psi4_command = _command_for_template("psi4", row.get("psi4_template_path"), engine_paths)
        openmm_command = _command_for_template("openmm", row.get("openmm_template_path"), engine_paths)
        vina_command = _command_for_template("vina", row.get("vina_template_path"), engine_paths)
        vqe_command = _command_for_template("qiskit_nature", row.get("qiskit_nature_vqe_template_path"), engine_paths)
        required = {
            "xtb": bool(xtb_command),
            "psi4": bool(psi4_command),
            "openmm": bool(openmm_command),
            "vina": bool(vina_command),
            "qiskit_nature": bool(vqe_command),
        }
        missing = [name for name, needed in required.items() if needed and not engine_state.get(name, False)]
        input_blockers = _template_input_blockers(
            row.get("xtb_template_path"),
            row.get("psi4_template_path"),
            row.get("openmm_template_path"),
            row.get("vina_template_path"),
            row.get("qiskit_nature_vqe_template_path"),
        )
        if missing:
            execution_status = "blocked_engines_missing"
        elif input_blockers:
            execution_status = "needs_reviewed_coordinates"
        elif any(required.values()):
            execution_status = "ready_to_execute"
        else:
            execution_status = "needs_templates"
        rows.append(
            {
                "gene": row.get("gene"),
                "hgvs_p": row.get("hgvs_p"),
                "model_request_id": row.get("model_request_id"),
                "surrogate_structural_signal_percent": row.get("surrogate_structural_signal_percent"),
                "drug_discovery_readiness_percent": row.get("drug_discovery_readiness_percent"),
                "prime_quantum_structural_alignment_percent": row.get("prime_quantum_structural_alignment_percent"),
                "preferred_coordinate_source": "AlphaFold DB" if reference_record else "",
                "alphafold_entry_id": reference_record.get("entry_id"),
                "alphafold_pdb_url": reference_record.get("pdb_url"),
                "alphafold_cif_url": reference_record.get("cif_url"),
                "xtb_command": xtb_command,
                "psi4_command": psi4_command,
                "openmm_command": openmm_command,
                "vina_command": vina_command,
                "qiskit_nature_vqe_command": vqe_command,
                "missing_engines": ", ".join(missing),
                "input_blockers": "; ".join(input_blockers),
                "execution_status": execution_status,
                "real_execution_completed": False,
                "result_artifact_path": "",
            }
        )
    return pd.DataFrame(rows)


def _write_environment_file(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "name: primevarclass-structural-engines",
                "channels:",
                "  - conda-forge",
                "dependencies:",
                "  - python>=3.11",
                "  - pandas",
                "  - numpy",
                "  - scipy",
                "  - rdkit",
                "  - openbabel",
                "  - xtb",
                "  - psi4",
                "  - openmm",
                "  - pdbfixer",
                "  - vina",
                "  - pip",
                "  - pip:",
                "      - qiskit-nature",
                "      - qiskit-algorithms",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _write_install_script(path: Path, env_path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "$ErrorActionPreference = 'Stop'",
                "$envFile = " + _quote_path(env_path),
                "if (Get-Command micromamba -ErrorAction SilentlyContinue) {",
                "  micromamba create -y -f $envFile",
                "  Write-Host 'Created primevarclass-structural-engines with micromamba.'",
                "} elseif (Get-Command mamba -ErrorAction SilentlyContinue) {",
                "  mamba env create -f $envFile",
                "  Write-Host 'Created primevarclass-structural-engines with mamba.'",
                "} elseif (Get-Command conda -ErrorAction SilentlyContinue) {",
                "  conda env create -f $envFile",
                "  Write-Host 'Created primevarclass-structural-engines with conda.'",
                "} else {",
                "  throw 'Install micromamba, mamba, or conda first, then rerun this script.'",
                "}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _write_doctor_script(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "$ErrorActionPreference = 'Continue'",
                "Write-Host 'PrimeVarClass structural engine doctor'",
                "$prefix = $env:PRIMEVARCLASS_STRUCTURAL_ENGINE_PREFIX",
                "if ([string]::IsNullOrWhiteSpace($prefix)) { $prefix = 'C:\\primevarclass_mamba\\envs\\primevarclass-structural-engines' }",
                "$env:PATH = \"$prefix\\Library\\bin;$prefix\\Scripts;$prefix\\bin;$env:PATH\"",
                "foreach ($cmd in @('xtb','psi4','vina','autodock_vina','qvina2','qvina','obabel')) {",
                "  $found = Get-Command $cmd -ErrorAction SilentlyContinue",
                "  if ($found) { Write-Host \"${cmd}: available at $($found.Source)\" }",
                "  else { Write-Host \"${cmd}: missing\" }",
                "}",
                "@'",
                "import importlib.util",
                "for module in ['openmm', 'qiskit_nature', 'qiskit_algorithms']:",
                "    print(f'{module}: ' + ('available' if importlib.util.find_spec(module) else 'missing'))",
                "'@ | python -",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _write_run_script(path: Path, queue_path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "$ErrorActionPreference = 'Stop'",
                "$queuePath = " + _quote_path(queue_path),
                "$queue = Import-Csv $queuePath",
                "foreach ($row in $queue) {",
                "  Write-Host \"BRCA1 $($row.hgvs_p): $($row.execution_status)\"",
                "  if ($row.execution_status -ne 'ready_to_execute') { continue }",
                "  foreach ($field in @('xtb_command','psi4_command','openmm_command','vina_command','qiskit_nature_vqe_command')) {",
                "    $cmd = $row.$field",
                "    if ([string]::IsNullOrWhiteSpace($cmd)) { continue }",
                "    Write-Host \"Running $field: $cmd\"",
                "    powershell -NoProfile -ExecutionPolicy Bypass -Command $cmd",
                "  }",
                "}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _execute_ready_rows(queue: pd.DataFrame, max_execute: int) -> pd.DataFrame:
    if queue.empty or max_execute <= 0:
        return pd.DataFrame()
    records: list[dict[str, Any]] = []
    ready = queue.loc[queue["execution_status"].eq("ready_to_execute")].head(max_execute)
    for _, row in ready.iterrows():
        for field in ["xtb_command", "psi4_command", "openmm_command", "vina_command", "qiskit_nature_vqe_command"]:
            command = str(row.get(field) or "").strip()
            if not command:
                continue
            started_at = _now_utc()
            try:
                completed = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=3600)
                status = "completed" if completed.returncode == 0 else "failed"
                stdout = (completed.stdout or "")[-2000:]
                stderr = (completed.stderr or "")[-2000:]
                return_code = completed.returncode
            except Exception as exc:
                status = "failed"
                stdout = ""
                stderr = str(exc)
                return_code = -1
            records.append(
                {
                    "gene": row.get("gene"),
                    "hgvs_p": row.get("hgvs_p"),
                    "command_field": field,
                    "command": command,
                    "started_at": started_at,
                    "finished_at": _now_utc(),
                    "status": status,
                    "return_code": return_code,
                    "stdout_tail": stdout,
                    "stderr_tail": stderr,
                }
            )
    return pd.DataFrame(records)


def _download_reference_structures(alphafold_metadata: dict[str, Any], output_root: Path) -> dict[str, str]:
    records = alphafold_metadata.get("records") or []
    if not records:
        return {}
    output_dir = output_root / "reference_structures"
    output_dir.mkdir(parents=True, exist_ok=True)
    first = records[0]
    downloaded: dict[str, str] = {}
    for key, suffix in [("pdb_url", ".pdb"), ("cif_url", ".cif")]:
        url = first.get(key)
        if not url:
            continue
        destination = output_dir / f"{first.get('entry_id') or 'alphafold_reference'}{suffix}"
        if destination.exists() and destination.stat().st_size > 0:
            downloaded[key.replace("_url", "_path")] = str(destination)
            continue
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "PrimeVarClass/1.0"})
            with urllib.request.urlopen(request, timeout=120) as response:
                destination.write_bytes(response.read())
            downloaded[key.replace("_url", "_path")] = str(destination)
        except Exception:
            continue
    return downloaded


def _build_input_preparation_queue(queue: pd.DataFrame, reference_paths: dict[str, str]) -> pd.DataFrame:
    if queue.empty or "input_blockers" not in queue.columns:
        return pd.DataFrame()
    blocked = queue.loc[queue["input_blockers"].fillna("").astype(str).ne("")].copy()
    if blocked.empty:
        return pd.DataFrame()
    blocked["reference_pdb_path"] = reference_paths.get("pdb_path", "")
    blocked["reference_cif_path"] = reference_paths.get("cif_path", "")
    blocked["next_input_step"] = (
        "Extract reviewed local residue environment from AlphaFold/reference structure, "
        "build mutant fragment coordinates, then replace placeholder xTB/Psi4/OpenMM/Vina/VQE inputs."
    )
    keep = [
        "gene",
        "hgvs_p",
        "model_request_id",
        "input_blockers",
        "reference_pdb_path",
        "reference_cif_path",
        "next_input_step",
    ]
    return blocked[[column for column in keep if column in blocked.columns]]


def _build_markdown(payload: dict[str, Any]) -> str:
    summary = dict(payload.get("summary") or {})
    engine_state = dict(payload.get("engine_state") or {})
    lines = [
        "# PrimeVarClass BRCA1 Real-Engine Execution Package",
        "",
        f"- Generated at: `{summary.get('generated_at')}`",
        f"- Queue targets: `{summary.get('queue_target_count', 0)}`",
        f"- AlphaFold reference available: `{summary.get('alphafold_reference_available')}`",
        f"- Engine availability: `{summary.get('engine_availability_percent', 0)}%`",
        f"- Missing engines: `{summary.get('engine_missing_count', 0)}`",
        f"- Execution preflight: `{summary.get('execution_preflight_status')}`",
        f"- Ready-to-execute targets: `{summary.get('ready_to_execute_target_count', 0)}`",
        f"- Targets needing reviewed coordinates/inputs: `{summary.get('input_blocked_target_count', 0)}`",
        f"- Blocked targets: `{summary.get('blocked_target_count', 0)}`",
        f"- Execution readiness: `{summary.get('execution_readiness_percent', 0)}%`",
        f"- Real executions completed now: `{summary.get('real_execution_completed_count', 0)}`",
        "",
        "## Engine status",
        "",
    ]
    for name, available in engine_state.items():
        lines.append(f"- {name}: `{'available' if available else 'missing'}`")
    lines.extend(
        [
            "",
            "## What this closes",
            "",
            "- The BRCA1 campaign now has a concrete execution queue, environment file, installer, runner, and AlphaFold coordinate source.",
            "- If engines are missing, the package records that blocker instead of fabricating xTB/DFT/VQE evidence.",
            "- Once the environment is installed, rerunning this package can execute the ready rows and preserve command logs.",
        ]
    )
    return "\n".join(lines).strip()


def build_brca1_engine_execution_package(
    *,
    brca1_structural_campaign_manifest_path: str,
    uniprot_id: str = BRCA1_UNIPROT_ID,
    timeout_sec: int = 20,
    execute_if_available: bool = False,
    max_execute: int = 3,
) -> dict[str, Any]:
    campaign_manifest = _load_json(brca1_structural_campaign_manifest_path)
    campaign_table = _read_table(campaign_manifest.get("campaign_path"))
    engine_state = _engine_status()
    engine_paths = _engine_paths()
    engine_diagnostics = _engine_diagnostics(engine_state, engine_paths)
    alphafold_metadata = _fetch_alphafold_metadata(uniprot_id, timeout_sec=timeout_sec)
    queue = _build_execution_queue(campaign_table, engine_state, engine_paths, alphafold_metadata)
    execution_log = _execute_ready_rows(queue, max_execute=max_execute) if execute_if_available else pd.DataFrame()
    if not execution_log.empty and not queue.empty:
        completed_pairs = {
            (row["gene"], row["hgvs_p"])
            for row in execution_log.loc[execution_log["status"].eq("completed")].to_dict(orient="records")
        }
        queue["real_execution_completed"] = queue.apply(
            lambda row: (row.get("gene"), row.get("hgvs_p")) in completed_pairs,
            axis=1,
        )
    target_count = int(len(queue))
    engine_availability = _percent((sum(1 for available in engine_state.values() if available) / max(len(engine_state), 1)) * 100)
    engine_missing_count = int((~engine_diagnostics["available"]).sum()) if not engine_diagnostics.empty else 0
    coordinate_coverage = 100 if alphafold_metadata.get("status") == "found" else 0
    template_coverage = _percent(
        queue[["xtb_command", "psi4_command", "openmm_command", "vina_command", "qiskit_nature_vqe_command"]]
        .astype(str)
        .replace("nan", "")
        .apply(lambda row: any(str(value).strip() for value in row), axis=1)
        .mean()
        * 100
        if target_count
        else 0
    )
    ready_count = int(queue["execution_status"].eq("ready_to_execute").sum()) if target_count else 0
    blocked_count = int(queue["execution_status"].eq("blocked_engines_missing").sum()) if target_count else 0
    input_blocked_count = int(queue["execution_status"].eq("needs_reviewed_coordinates").sum()) if target_count else 0
    execution_readiness = _percent(
        (template_coverage * 0.30)
        + (coordinate_coverage * 0.25)
        + (engine_availability * 0.30)
        + ((100 - _percent((input_blocked_count / target_count) * 100 if target_count else 0)) * 0.15)
    )
    summary = {
        "generated_at": _now_utc(),
        "queue_target_count": target_count,
        "alphafold_reference_available": alphafold_metadata.get("status") == "found",
        "alphafold_record_count": int(alphafold_metadata.get("record_count") or 0),
        "engine_availability_percent": engine_availability,
        "engine_missing_count": engine_missing_count,
        "engine_doctor_pass_percent": engine_availability,
        "template_coverage_percent": template_coverage,
        "ready_to_execute_target_count": ready_count,
        "blocked_target_count": blocked_count,
        "input_blocked_target_count": input_blocked_count,
        "real_execution_completed_count": int(queue["real_execution_completed"].sum()) if target_count else 0,
        "execution_readiness_percent": execution_readiness,
        "ready_for_executed_physics_claims": ready_count > 0 and blocked_count == 0 and input_blocked_count == 0,
        "execution_preflight_status": (
            "ready"
            if ready_count > 0 and blocked_count == 0 and input_blocked_count == 0
            else "blocked_missing_engines"
            if blocked_count
            else "blocked_needs_reviewed_coordinates"
        ),
        "source_brca1_structural_campaign_manifest_path": str(Path(brca1_structural_campaign_manifest_path).expanduser().resolve()),
        "public_sources": {
            "alphafold_api_url": ALPHAFOLD_API_URL.format(uniprot_id=uniprot_id),
            "uniprot_id": uniprot_id,
        },
        "guardrail": "This package only upgrades to executed physics when the real engines are installed and command logs exist.",
    }
    payload = {
        "summary": summary,
        "engine_state": engine_state,
        "engine_paths": engine_paths,
        "engine_diagnostics": engine_diagnostics,
        "alphafold_metadata": alphafold_metadata,
        "execution_queue": queue,
        "execution_log": execution_log,
    }
    payload["markdown_report"] = _build_markdown(payload)
    payload["html_report"] = _render_markdown_html(payload["markdown_report"], "PrimeVarClass BRCA1 Real-Engine Execution Package")
    return payload


def export_brca1_engine_execution_package(
    *,
    brca1_structural_campaign_manifest_path: str,
    output_dir: str,
    uniprot_id: str = BRCA1_UNIPROT_ID,
    timeout_sec: int = 20,
    execute_if_available: bool = False,
    max_execute: int = 3,
) -> dict[str, Any]:
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    payload = build_brca1_engine_execution_package(
        brca1_structural_campaign_manifest_path=brca1_structural_campaign_manifest_path,
        uniprot_id=uniprot_id,
        timeout_sec=timeout_sec,
        execute_if_available=execute_if_available,
        max_execute=max_execute,
    )

    queue_path = output_root / "brca1_engine_execution_queue.csv"
    execution_log_path = output_root / "brca1_engine_execution_log.csv"
    engine_diagnostics_path = output_root / "structural_engine_diagnostics.csv"
    input_preparation_queue_path = output_root / "brca1_input_preparation_queue.csv"
    alphafold_path = output_root / "brca1_alphafold_reference.json"
    environment_path = output_root / "environment.structural-engines.yml"
    install_script_path = output_root / "install_structural_engines.ps1"
    doctor_script_path = output_root / "check_structural_engines.ps1"
    run_script_path = output_root / "run_brca1_engine_campaign.ps1"
    markdown_path = output_root / "brca1_engine_execution_report.md"
    html_path = output_root / "brca1_engine_execution_report.html"
    manifest_path = output_root / "brca1_engine_execution_manifest.json"

    queue = payload.get("execution_queue")
    (queue if isinstance(queue, pd.DataFrame) else pd.DataFrame()).to_csv(queue_path, index=False, quoting=csv.QUOTE_MINIMAL)
    execution_log = payload.get("execution_log")
    (execution_log if isinstance(execution_log, pd.DataFrame) else pd.DataFrame()).to_csv(execution_log_path, index=False)
    engine_diagnostics = payload.get("engine_diagnostics")
    (engine_diagnostics if isinstance(engine_diagnostics, pd.DataFrame) else pd.DataFrame()).to_csv(engine_diagnostics_path, index=False)
    alphafold_path.write_text(json.dumps(_jsonify(payload.get("alphafold_metadata") or {}), indent=2, ensure_ascii=False), encoding="utf-8")
    reference_paths = _download_reference_structures(payload.get("alphafold_metadata") or {}, output_root)
    input_preparation_queue = _build_input_preparation_queue(queue if isinstance(queue, pd.DataFrame) else pd.DataFrame(), reference_paths)
    input_preparation_queue.to_csv(input_preparation_queue_path, index=False)
    _write_environment_file(environment_path)
    _write_install_script(install_script_path, environment_path)
    _write_doctor_script(doctor_script_path)
    _write_run_script(run_script_path, queue_path)
    markdown_path.write_text(str(payload.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(str(payload.get("html_report") or ""), encoding="utf-8")

    manifest_payload = {
        "generated_at": _now_utc(),
        "summary": payload.get("summary") or {},
        "engine_state": payload.get("engine_state") or {},
        "engine_paths": payload.get("engine_paths") or {},
        "execution_queue_path": str(queue_path),
        "execution_log_path": str(execution_log_path),
        "engine_diagnostics_path": str(engine_diagnostics_path),
        "input_preparation_queue_path": str(input_preparation_queue_path),
        "alphafold_reference_path": str(alphafold_path),
        "reference_structure_paths": reference_paths,
        "environment_path": str(environment_path),
        "install_script_path": str(install_script_path),
        "doctor_script_path": str(doctor_script_path),
        "run_script_path": str(run_script_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
    }
    manifest_path.write_text(json.dumps(_jsonify(manifest_payload), indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "brca1_engine_execution": payload,
        "brca1_engine_execution_manifest_path": str(manifest_path),
        "brca1_engine_execution_queue_path": str(queue_path),
        "brca1_engine_execution_log_path": str(execution_log_path),
        "structural_engine_diagnostics_path": str(engine_diagnostics_path),
        "brca1_input_preparation_queue_path": str(input_preparation_queue_path),
        "brca1_alphafold_reference_path": str(alphafold_path),
        "brca1_reference_structure_paths": reference_paths,
        "structural_engine_environment_path": str(environment_path),
        "structural_engine_install_script_path": str(install_script_path),
        "structural_engine_doctor_script_path": str(doctor_script_path),
        "brca1_engine_run_script_path": str(run_script_path),
        "brca1_engine_execution_report_markdown_path": str(markdown_path),
        "brca1_engine_execution_report_html_path": str(html_path),
    }
