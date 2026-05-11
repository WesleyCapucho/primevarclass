from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _load_json(path: str) -> dict[str, Any]:
    candidate = Path(path)
    if not candidate.exists():
        raise FileNotFoundError(f"Manifesto nao encontrado: {path}")
    return json.loads(candidate.read_text(encoding="utf-8"))


def _relative_posix(path: Path, workspace_root: Path) -> str:
    return path.resolve().relative_to(workspace_root.resolve()).as_posix()


def _load_rollout_table(rollout_manifest: dict[str, Any]) -> pd.DataFrame:
    csv_path = rollout_manifest.get("rollout_csv_path")
    if csv_path and Path(csv_path).exists():
        return pd.read_csv(csv_path)
    rows: list[dict[str, Any]] = []
    summary = rollout_manifest.get("summary") or {}
    for phase_name in ["phase_1_genes", "phase_2_genes", "phase_3_genes"]:
        phase_label = phase_name.replace("_genes", "")
        for rank, gene in enumerate(summary.get(phase_name, []), start=1):
            rows.append({"gene": gene, "rank": rank, "rollout_phase": phase_label})
    return pd.DataFrame(rows)


def _placeholder_training_dataframe(gene: str) -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "gene",
            "hgvs_p",
            "label",
            "review_status",
            "clinical_significance",
            "variant_id",
            "source",
        ]
    ).assign(gene=pd.Series(dtype="string")).astype({"gene": "string"})


def _placeholder_gnomad_dataframe() -> pd.DataFrame:
    return pd.DataFrame(columns=["gene", "hgvs_p", "af", "ac", "an", "popmax_af"])


def _placeholder_mavedb_dataframe() -> pd.DataFrame:
    return pd.DataFrame(columns=["gene", "hgvs_p", "score", "score_set_urn", "assay_name"])


def _write_placeholder_table(path: Path, dataframe: pd.DataFrame, sep: str = "\t") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(path, sep=sep, index=False)


def _build_train_config_text(
    *,
    gene: str,
    training_path: Path,
    gnomad_path: Path,
    mavedb_path: Path,
    workspace_root: Path,
) -> str:
    return "\n".join(
        [
            "[ingestion]",
            'deduplicate_on = ["gene", "hgvs_p", "label"]',
            "prefer_annotation_values = true",
            "",
            "[[sources]]",
            f'name = "{gene.lower()}_training_clinvar_like"',
            'kind = "cohort"',
            'type = "file"',
            'format = "tsv"',
            f'path = "{_relative_posix(training_path, workspace_root)}"',
            'preset = "clinvar_variant_summary"',
            f'gene_allowlist = ["{gene}"]',
            "",
            "[[sources]]",
            f'name = "{gene.lower()}_gnomad_annotations"',
            'kind = "annotation"',
            'type = "file"',
            'format = "tsv"',
            f'path = "{_relative_posix(gnomad_path, workspace_root)}"',
            'preset = "gnomad_variant_table"',
            'join_on = ["gene", "hgvs_p"]',
            f'gene_allowlist = ["{gene}"]',
            "",
            "[[sources]]",
            f'name = "{gene.lower()}_mavedb_scores"',
            'kind = "annotation"',
            'type = "file"',
            'format = "csv"',
            f'path = "{_relative_posix(mavedb_path, workspace_root)}"',
            'preset = "mavedb_score_table"',
            'join_on = ["gene", "hgvs_p"]',
            f'gene_allowlist = ["{gene}"]',
            "",
        ]
    )


def _build_external_config_text(
    *,
    gene: str,
    cohort_name: str,
    external_path: Path,
    gnomad_path: Path,
    mavedb_path: Path,
    workspace_root: Path,
) -> str:
    return "\n".join(
        [
            "[ingestion]",
            'deduplicate_on = ["gene", "hgvs_p", "label"]',
            "prefer_annotation_values = true",
            "",
            "[[sources]]",
            f'name = "{cohort_name}"',
            'kind = "cohort"',
            'type = "file"',
            'format = "tsv"',
            f'path = "{_relative_posix(external_path, workspace_root)}"',
            'preset = "clinvar_variant_summary"',
            f'gene_allowlist = ["{gene}"]',
            "",
            "[[sources]]",
            f'name = "{gene.lower()}_validation_gnomad_annotations"',
            'kind = "annotation"',
            'type = "file"',
            'format = "tsv"',
            f'path = "{_relative_posix(gnomad_path, workspace_root)}"',
            'preset = "gnomad_variant_table"',
            'join_on = ["gene", "hgvs_p"]',
            f'gene_allowlist = ["{gene}"]',
            "",
            "[[sources]]",
            f'name = "{gene.lower()}_validation_mavedb_scores"',
            'kind = "annotation"',
            'type = "file"',
            'format = "csv"',
            f'path = "{_relative_posix(mavedb_path, workspace_root)}"',
            'preset = "mavedb_score_table"',
            'join_on = ["gene", "hgvs_p"]',
            f'gene_allowlist = ["{gene}"]',
            "",
        ]
    )


def _build_benchmark_text(
    *,
    gene: str,
    train_config_path: Path,
    external_config_paths: list[tuple[str, Path]],
    workspace_root: Path,
) -> str:
    lines = [
        "[study]",
        f'name = "Public {gene} Benchmark Scaffold"',
        'mode = "hybrid"',
        "high_confidence_only = false",
        "keep_metadata = true",
        'primary_metric = "auc_roc"',
        'baseline_experiment = "external_predictors_only"',
        "n_bootstrap = 100",
        "",
        "[[cohorts]]",
        f'name = "{gene.lower()}_training"',
        'role = "train"',
        f'source_config = "{_relative_posix(train_config_path, workspace_root)}"',
        "",
    ]
    for cohort_name, config_path in external_config_paths:
        lines.extend(
            [
                "[[cohorts]]",
                f'name = "{cohort_name}"',
                'role = "external_test"',
                f'source_config = "{_relative_posix(config_path, workspace_root)}"',
                "",
            ]
        )
    return "\n".join(lines)


def _build_markdown(summary: dict[str, Any], tasks: pd.DataFrame, scaffold_index: pd.DataFrame) -> str:
    lines = [
        "# PrimeVarClass Multigene Study Factory",
        "",
        f"- Generated at: `{summary['generated_at']}`",
        f"- Total scaffolded genes: `{summary['total_scaffolded_genes']}`",
        f"- Phase 1 genes: `{', '.join(summary['phase_1_genes']) if summary['phase_1_genes'] else 'none'}`",
        f"- Phase 2 genes: `{', '.join(summary['phase_2_genes']) if summary['phase_2_genes'] else 'none'}`",
        "",
        "## Recommended Next Move",
        "",
        f"- Start with `{summary['phase_1_genes'][0]}` as the first multigene real benchmark." if summary["phase_1_genes"] else "- No phase 1 gene selected.",
        "",
        "## Scaffold Index",
        "",
    ]
    if scaffold_index.empty:
        lines.append("_No scaffolded genes._")
    else:
        header = "| " + " | ".join(scaffold_index.columns) + " |"
        divider = "| " + " | ".join("---" for _ in scaffold_index.columns) + " |"
        body = ["| " + " | ".join(str(value) for value in row) + " |" for row in scaffold_index.itertuples(index=False, name=None)]
        lines.extend([header, divider, *body])
    lines.extend(["", "## Data Tasks", ""])
    if tasks.empty:
        lines.append("_No tasks generated._")
    else:
        header = "| " + " | ".join(tasks.columns) + " |"
        divider = "| " + " | ".join("---" for _ in tasks.columns) + " |"
        body = ["| " + " | ".join(str(value) for value in row) + " |" for row in tasks.itertuples(index=False, name=None)]
        lines.extend([header, divider, *body])
    return "\n".join(lines)


def export_multigene_study_factory(
    rollout_manifest_path: str,
    output_dir: str = "primevarclass_multigene_study_factory_results",
    workspace_root: str | None = None,
    include_phases: list[str] | None = None,
) -> dict[str, Any]:
    rollout_manifest = _load_json(rollout_manifest_path)
    rollout_table = _load_rollout_table(rollout_manifest)
    selected_phases = include_phases or ["phase_1_immediate", "phase_2_expansion"]
    selected = rollout_table[rollout_table["rollout_phase"].isin(selected_phases)].copy()
    selected = selected.sort_values(["rank", "expansion_priority_percent"], ascending=[True, False]).reset_index(drop=True)

    root = Path(workspace_root).resolve() if workspace_root else Path(__file__).resolve().parents[2]
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    scaffold_rows: list[dict[str, Any]] = []
    task_rows: list[dict[str, Any]] = []

    for row in selected.to_dict(orient="records"):
        gene = str(row["gene"]).strip().upper()
        gene_slug = gene.lower()
        data_dir = root / "data" / "raw" / "multigene" / gene_slug
        config_dir = root / "configs" / "multigene" / gene_slug
        training_path = data_dir / f"{gene_slug}_clinvar_training.tsv"
        external_clinical_path = data_dir / f"{gene_slug}_clinical_external.tsv"
        external_secondary_path = data_dir / f"{gene_slug}_secondary_external.tsv"
        gnomad_path = root / "data" / "raw" / "gnomad" / f"{gene_slug}_missense_annotations.tsv"
        mavedb_path = root / "data" / "raw" / "mavedb" / f"{gene_slug}_function_scores.csv"

        _write_placeholder_table(training_path, _placeholder_training_dataframe(gene), sep="\t")
        _write_placeholder_table(external_clinical_path, _placeholder_training_dataframe(gene), sep="\t")
        _write_placeholder_table(external_secondary_path, _placeholder_training_dataframe(gene), sep="\t")
        _write_placeholder_table(gnomad_path, _placeholder_gnomad_dataframe(), sep="\t")
        _write_placeholder_table(mavedb_path, _placeholder_mavedb_dataframe(), sep=",")

        config_dir.mkdir(parents=True, exist_ok=True)
        train_config_path = config_dir / f"public_{gene_slug}_real.toml"
        external_clinical_config_path = config_dir / f"public_{gene_slug}_external_clinical.toml"
        external_secondary_config_path = config_dir / f"public_{gene_slug}_external_secondary.toml"
        benchmark_config_path = config_dir / f"public_{gene_slug}_benchmark.toml"

        train_config_path.write_text(
            _build_train_config_text(
                gene=gene,
                training_path=training_path,
                gnomad_path=gnomad_path,
                mavedb_path=mavedb_path,
                workspace_root=root,
            ),
            encoding="utf-8",
        )
        external_clinical_config_path.write_text(
            _build_external_config_text(
                gene=gene,
                cohort_name=f"{gene_slug}_clinical_external_validation",
                external_path=external_clinical_path,
                gnomad_path=gnomad_path,
                mavedb_path=mavedb_path,
                workspace_root=root,
            ),
            encoding="utf-8",
        )
        external_secondary_config_path.write_text(
            _build_external_config_text(
                gene=gene,
                cohort_name=f"{gene_slug}_secondary_external_validation",
                external_path=external_secondary_path,
                gnomad_path=gnomad_path,
                mavedb_path=mavedb_path,
                workspace_root=root,
            ),
            encoding="utf-8",
        )
        benchmark_config_path.write_text(
            _build_benchmark_text(
                gene=gene,
                train_config_path=train_config_path,
                external_config_paths=[
                    (f"{gene_slug}_clinical_external_validation", external_clinical_config_path),
                    (f"{gene_slug}_secondary_external_validation", external_secondary_config_path),
                ],
                workspace_root=root,
            ),
            encoding="utf-8",
        )

        scaffold_rows.append(
            {
                "gene": gene,
                "rollout_phase": row.get("rollout_phase"),
                "prime_priority": row.get("prime_priority"),
                "benchmark_config_path": str(benchmark_config_path.resolve()),
                "train_config_path": str(train_config_path.resolve()),
                "external_clinical_config_path": str(external_clinical_config_path.resolve()),
                "external_secondary_config_path": str(external_secondary_config_path.resolve()),
            }
        )
        for artifact_name, path in [
            ("training_clinvar_like", training_path),
            ("external_clinical", external_clinical_path),
            ("external_secondary", external_secondary_path),
            ("gnomad_annotations", gnomad_path),
            ("mavedb_scores", mavedb_path),
        ]:
            task_rows.append(
                {
                    "gene": gene,
                    "rollout_phase": row.get("rollout_phase"),
                    "artifact": artifact_name,
                    "path": str(path.resolve()),
                    "status": "placeholder_created",
                }
            )

    scaffold_index = pd.DataFrame(scaffold_rows)
    tasks = pd.DataFrame(task_rows)

    summary = {
        "generated_at": _now_utc(),
        "workspace_root": str(root),
        "total_scaffolded_genes": int(len(scaffold_index)),
        "phase_1_genes": selected.loc[selected["rollout_phase"] == "phase_1_immediate", "gene"].astype(str).tolist(),
        "phase_2_genes": selected.loc[selected["rollout_phase"] == "phase_2_expansion", "gene"].astype(str).tolist(),
        "phase_3_genes": selected.loc[selected["rollout_phase"] == "phase_3_exploration", "gene"].astype(str).tolist(),
    }

    scaffold_index_path = output_root / "multigene_study_scaffold_index.csv"
    tasks_path = output_root / "multigene_study_factory_tasks.csv"
    markdown_path = output_root / "multigene_study_factory.md"
    manifest_path = output_root / "multigene_study_factory_manifest.json"

    scaffold_index.to_csv(scaffold_index_path, index=False)
    tasks.to_csv(tasks_path, index=False)
    markdown_path.write_text(_build_markdown(summary, tasks, scaffold_index), encoding="utf-8")

    manifest = {
        "generated_at": summary["generated_at"],
        "summary": summary,
        "rollout_manifest_path": str(Path(rollout_manifest_path).resolve()),
        "scaffold_index_path": str(scaffold_index_path.resolve()),
        "tasks_path": str(tasks_path.resolve()),
        "markdown_path": str(markdown_path.resolve()),
        "manifest_path": str(manifest_path.resolve()),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
