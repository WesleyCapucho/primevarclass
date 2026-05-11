from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _safe_float(value: Any) -> float:
    try:
        numeric = float(value)
    except Exception:
        return float("nan")
    if np.isnan(numeric):
        return float("nan")
    return numeric


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _status_from_percent(value: int) -> str:
    if value >= 85:
        return "ready"
    if value >= 60:
        return "partial"
    return "gap"


def _variant_keys(df: pd.DataFrame) -> pd.Series:
    if "gene" in df.columns and "hgvs_p" in df.columns:
        return (
            df["gene"].astype(str).str.upper().str.strip()
            + "::"
            + df["hgvs_p"].astype(str).str.strip()
        )
    if "variant" in df.columns:
        return df["variant"].astype(str).str.strip()
    return pd.Series([f"row_{index}" for index in range(len(df))], index=df.index, dtype="object")


def _gene_keys(df: pd.DataFrame) -> pd.Series:
    if "gene" in df.columns:
        return df["gene"].astype(str).str.upper().str.strip()
    return pd.Series(["unknown"] * len(df), index=df.index, dtype="object")


def _label_map(df: pd.DataFrame) -> dict[str, set[int]]:
    if "label" not in df.columns:
        return {}
    keys = _variant_keys(df)
    rows: dict[str, set[int]] = {}
    for key, label in zip(keys.tolist(), df["label"].tolist()):
        try:
            parsed_label = int(label)
        except Exception:
            continue
        rows.setdefault(str(key), set()).add(parsed_label)
    return rows


def _safe_percent(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return (numerator / denominator) * 100.0


def build_cohort_independence_assessment(cohort_tables: List[dict]) -> dict:
    cohort_rows: List[dict] = []
    prepared = []
    for item in cohort_tables:
        name = str(item.get("cohort_name") or item.get("name") or "unknown")
        role = str(item.get("role") or "external_test")
        df = item.get("dataframe")
        frame = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()

        variant_keys = set(_variant_keys(frame).dropna().astype(str).tolist()) if not frame.empty else set()
        gene_keys = set(_gene_keys(frame).dropna().astype(str).tolist()) if not frame.empty else set()
        label_map = _label_map(frame)
        cohort_rows.append(
            {
                "cohort_name": name,
                "role": role,
                "n_rows": int(len(frame)),
                "n_unique_variants": int(len(variant_keys)),
                "n_unique_genes": int(len(gene_keys)),
                "has_labels": bool("label" in frame.columns),
            }
        )
        prepared.append(
            {
                "cohort_name": name,
                "role": role,
                "variant_keys": variant_keys,
                "gene_keys": gene_keys,
                "label_map": label_map,
            }
        )

    pair_rows: List[dict] = []
    for index, left in enumerate(prepared):
        for right in prepared[index + 1 :]:
            shared_variants = sorted(left["variant_keys"] & right["variant_keys"])
            shared_genes = sorted(left["gene_keys"] & right["gene_keys"])
            smaller_variant_count = min(len(left["variant_keys"]), len(right["variant_keys"]))
            smaller_gene_count = min(len(left["gene_keys"]), len(right["gene_keys"]))
            conflicting_labels = 0
            for variant_key in shared_variants:
                left_labels = left["label_map"].get(variant_key, set())
                right_labels = right["label_map"].get(variant_key, set())
                if left_labels and right_labels and left_labels != right_labels:
                    conflicting_labels += 1

            pair_role = "train_external" if {left["role"], right["role"]} == {"train", "external_test"} or (
                "train" in {left["role"], right["role"]} and len({left["role"], right["role"]}) == 2
            ) else f"{left['role']}__{right['role']}"

            pair_rows.append(
                {
                    "left_cohort": left["cohort_name"],
                    "left_role": left["role"],
                    "right_cohort": right["cohort_name"],
                    "right_role": right["role"],
                    "pair_role": pair_role,
                    "shared_variant_count": int(len(shared_variants)),
                    "shared_variant_examples": ", ".join(shared_variants[:5]),
                    "shared_variant_percent_smaller": round(_safe_percent(len(shared_variants), smaller_variant_count), 2),
                    "shared_gene_count": int(len(shared_genes)),
                    "shared_gene_examples": ", ".join(shared_genes[:5]),
                    "shared_gene_percent_smaller": round(_safe_percent(len(shared_genes), smaller_gene_count), 2),
                    "label_conflict_count": int(conflicting_labels),
                    "has_exact_variant_overlap": bool(shared_variants),
                    "has_label_conflict": bool(conflicting_labels > 0),
                }
            )

    pair_df = pd.DataFrame(pair_rows)
    cohort_df = pd.DataFrame(cohort_rows)

    train_external_df = pair_df[pair_df["pair_role"].astype(str) == "train_external"].copy() if not pair_df.empty else pd.DataFrame()
    if train_external_df.empty:
        overall_percent = 0
        max_variant_overlap_percent = 0
        mean_variant_overlap_percent = 0
        variant_overlap_pair_rate_percent = 0
        label_conflict_pair_rate_percent = 0
    else:
        max_variant_overlap_percent = _safe_int(train_external_df["shared_variant_percent_smaller"].max())
        mean_variant_overlap_percent = _safe_int(train_external_df["shared_variant_percent_smaller"].mean())
        variant_overlap_pair_rate_percent = _safe_int(train_external_df["has_exact_variant_overlap"].mean() * 100)
        label_conflict_pair_rate_percent = _safe_int(train_external_df["has_label_conflict"].mean() * 100)
        overall_percent = int(
            round(
                max(
                    0.0,
                    100.0
                    - (mean_variant_overlap_percent * 1.2)
                    - (variant_overlap_pair_rate_percent * 0.35)
                    - (label_conflict_pair_rate_percent * 0.6),
                )
            )
        )

    critical_gaps = []
    if label_conflict_pair_rate_percent > 0:
        critical_gaps.append("Cross-cohort label conflicts")
    if max_variant_overlap_percent > 0:
        critical_gaps.append("Exact train/external variant overlap")

    recommended_actions = []
    if max_variant_overlap_percent > 0:
        recommended_actions.append("Remover variantes duplicadas entre treino e validacao externa antes da rodada final.")
    if label_conflict_pair_rate_percent > 0:
        recommended_actions.append("Resolver variantes com rotulos conflitantes entre coortes para evitar leakage semantico.")
    if not train_external_df.empty and overall_percent < 85:
        recommended_actions.append("Preservar independencia mais forte entre coortes de treino e avaliacao para sustentar a validacao externa.")

    markdown_lines = [
        "# Cohort Independence Audit",
        "",
        f"- Generated at: {_now_utc()}",
        f"- Overall independence: {overall_percent}%",
        f"- Train/external pairs: {int(len(train_external_df))}",
        f"- Max exact variant overlap: {max_variant_overlap_percent}%",
        f"- Label-conflict pair rate: {label_conflict_pair_rate_percent}%",
        "",
        "## Cohort Snapshot",
        "",
    ]
    if cohort_df.empty:
        markdown_lines.append("- Nenhuma coorte analisada.")
    else:
        for _, row in cohort_df.iterrows():
            markdown_lines.append(
                f"- {row['cohort_name']} ({row['role']}): rows={int(row['n_rows'])}, "
                f"unique_variants={int(row['n_unique_variants'])}, unique_genes={int(row['n_unique_genes'])}"
            )

    markdown_lines.extend(["", "## Pairwise Audit", ""])
    if pair_df.empty:
        markdown_lines.append("- Nenhum par de coortes disponivel para auditoria.")
    else:
        for _, row in pair_df.iterrows():
            markdown_lines.append(
                f"- {row['left_cohort']} vs {row['right_cohort']} ({row['pair_role']}): "
                f"variant_overlap={row['shared_variant_count']} ({row['shared_variant_percent_smaller']}%), "
                f"gene_overlap={row['shared_gene_count']} ({row['shared_gene_percent_smaller']}%), "
                f"label_conflicts={row['label_conflict_count']}"
            )

    markdown_lines.extend(["", "## Recommended Actions", ""])
    if recommended_actions:
        for action in recommended_actions:
            markdown_lines.append(f"- {action}")
    else:
        markdown_lines.append("- Nenhum ajuste prioritario de independencia foi identificado.")

    return {
        "summary": {
            "generated_at": _now_utc(),
            "overall_independence_percent": overall_percent,
            "overall_status": _status_from_percent(overall_percent),
            "n_cohorts": int(len(cohort_df)),
            "n_pairs": int(len(pair_df)),
            "n_train_external_pairs": int(len(train_external_df)),
            "max_variant_overlap_percent": max_variant_overlap_percent,
            "mean_variant_overlap_percent": mean_variant_overlap_percent,
            "variant_overlap_pair_rate_percent": variant_overlap_pair_rate_percent,
            "label_conflict_pair_rate_percent": label_conflict_pair_rate_percent,
            "ready_for_external_validation": bool(
                not critical_gaps and overall_percent >= 85 and len(train_external_df) > 0
            ),
            "n_critical_gaps": int(len(critical_gaps)),
        },
        "critical_gaps": critical_gaps,
        "recommended_actions": recommended_actions,
        "cohorts": cohort_df.to_dict(orient="records"),
        "pairwise_audit": pair_df.to_dict(orient="records"),
        "markdown_report": "\n".join(markdown_lines).strip(),
    }


def build_cohort_independence_html(assessment: dict) -> str:
    markdown = str(assessment.get("markdown_report") or "")
    blocks: List[str] = []
    for block in markdown.split("\n\n"):
        stripped = block.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            blocks.append(f"<h1>{html.escape(stripped[2:])}</h1>")
            continue
        if stripped.startswith("## "):
            blocks.append(f"<h2>{html.escape(stripped[3:])}</h2>")
            continue
        if stripped.startswith("- "):
            items = "".join(f"<li>{html.escape(line[2:])}</li>" for line in stripped.splitlines() if line.startswith("- "))
            blocks.append(f"<ul>{items}</ul>")
            continue
        blocks.append(f"<p>{html.escape(stripped)}</p>")
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>PrimeVarClass Cohort Independence Audit</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f7f2ea;color:#17242f;max-width:980px;margin:0 auto;padding:32px;line-height:1.68;}"
        "h1{font-size:2.2rem;}h2{margin-top:2rem;color:#8b4b2a;}ul{background:#fff;border:1px solid #eadfce;border-radius:16px;padding:18px 24px;}"
        "</style></head><body>"
        + "".join(blocks)
        + "</body></html>"
    )


def export_cohort_independence_package(cohort_tables: List[dict], output_dir: str) -> dict:
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    assessment = build_cohort_independence_assessment(cohort_tables)
    html_report = build_cohort_independence_html(assessment)

    markdown_path = root / "cohort_independence_report.md"
    html_path = root / "cohort_independence_report.html"
    manifest_path = root / "cohort_independence_manifest.json"
    cohorts_path = root / "cohort_independence_cohorts.csv"
    pairwise_path = root / "cohort_independence_pairs.csv"

    markdown_path.write_text(str(assessment.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(html_report, encoding="utf-8")
    pd.DataFrame(assessment.get("cohorts") or []).to_csv(cohorts_path, index=False)
    pd.DataFrame(assessment.get("pairwise_audit") or []).to_csv(pairwise_path, index=False)
    manifest_payload = {
        "generated_at": _now_utc(),
        "summary": assessment.get("summary"),
        "critical_gaps": assessment.get("critical_gaps"),
        "recommended_actions": assessment.get("recommended_actions"),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "cohorts_path": str(cohorts_path),
        "pairwise_path": str(pairwise_path),
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "cohort_independence_assessment": assessment,
        "cohort_independence_report_markdown_path": str(markdown_path),
        "cohort_independence_report_html_path": str(html_path),
        "cohort_independence_manifest_path": str(manifest_path),
        "cohort_independence_cohorts_path": str(cohorts_path),
        "cohort_independence_pairs_path": str(pairwise_path),
    }
