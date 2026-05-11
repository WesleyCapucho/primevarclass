from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "C:\\Users\\Wesley Capucho\\Documents\\IA dos n\u00fameros primos\\src")

from primevarclass import (
    execute_public_source_bootstrap_bundle,
    export_public_source_resolution,
    ingest_sources_from_config,
    train_from_source_config,
)


CONFIG_PATH = "C:\\Users\\Wesley Capucho\\Documents\\IA dos n\u00fameros primos\\configs\\public_brca_example.toml"
BOOTSTRAP_OUTPUT_DIR = "C:\\Users\\Wesley Capucho\\Documents\\IA dos n\u00fameros primos\\primevarclass_continuous_learning_results\\bootstrap_workspace"
RESOLUTION_OUTPUT_DIR = "C:\\Users\\Wesley Capucho\\Documents\\IA dos n\u00fameros primos\\primevarclass_continuous_learning_results\\resolution_workspace"
TRAINING_OUTPUT_DIR = "C:\\Users\\Wesley Capucho\\Documents\\IA dos n\u00fameros primos\\primevarclass_continuous_learning_results\\training_workspace"
INGEST_OUTPUT_DIR = "C:\\Users\\Wesley Capucho\\Documents\\IA dos n\u00fameros primos\\primevarclass_continuous_learning_results\\catalog_snapshot"
LAST_RUN_PATH = "C:\\Users\\Wesley Capucho\\Documents\\IA dos n\u00fameros primos\\primevarclass_continuous_learning_results\\continuous_learning_last_run.json"
MODE = "hybrid"
HIGH_CONFIDENCE_ONLY = false
MODEL_FAMILIES = []
SELECTED_SOURCES = ["clinvar_variant_summary", "gnomad_brca_annotations"]


def main() -> None:
    Path(LAST_RUN_PATH).parent.mkdir(parents=True, exist_ok=True)
    ingestion = ingest_sources_from_config(CONFIG_PATH, output_dir=INGEST_OUTPUT_DIR)
    assessment = ingestion.get("public_source_assessment") or {}
    sync_plan = ingestion.get("public_source_sync_plan") or {}

    execution = {}
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

    payload = {
        "config_path": CONFIG_PATH,
        "resolved_config_path": resolved_config_path,
        "selected_sources": SELECTED_SOURCES,
        "execution_summary": execution.get("summary") or {},
        "training_summary_path": training.get("summary_report_path"),
        "training_metrics_path": training.get("export_paths", {}).get("metrics"),
        "catalog_readiness_percent": (assessment.get("summary") or {}).get("overall_readiness_percent"),
        "sync_candidates": (sync_plan.get("summary") or {}).get("n_sync_candidates"),
    }
    Path(LAST_RUN_PATH).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
