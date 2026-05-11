from __future__ import annotations

import hashlib
import html
import json
import re
import tarfile
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from io import TextIOWrapper
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from .source_presets import apply_source_preset

ALLOWED_GENES = {"BRCA1", "BRCA2"}
ALLOWED_LABELS = {
    "pathogenic": "Pathogenic",
    "likely pathogenic": "Likely pathogenic",
    "pathogenic/likely pathogenic": "Pathogenic/Likely pathogenic",
    "benign": "Benign",
    "likely benign": "Likely benign",
    "benign/likely benign": "Benign/Likely benign",
}
POSITIVE_LABELS = {"Pathogenic", "Likely pathogenic", "Pathogenic/Likely pathogenic"}
NEGATIVE_LABELS = {"Benign", "Likely benign", "Benign/Likely benign"}
AA3_CODES = {
    "Ala",
    "Arg",
    "Asn",
    "Asp",
    "Cys",
    "Gln",
    "Glu",
    "Gly",
    "His",
    "Ile",
    "Leu",
    "Lys",
    "Met",
    "Phe",
    "Pro",
    "Ser",
    "Thr",
    "Trp",
    "Tyr",
    "Val",
}
AA1_TO_AA3 = {
    "A": "Ala",
    "R": "Arg",
    "N": "Asn",
    "D": "Asp",
    "C": "Cys",
    "Q": "Gln",
    "E": "Glu",
    "G": "Gly",
    "H": "His",
    "I": "Ile",
    "L": "Leu",
    "K": "Lys",
    "M": "Met",
    "F": "Phe",
    "P": "Pro",
    "S": "Ser",
    "T": "Thr",
    "W": "Trp",
    "Y": "Tyr",
    "V": "Val",
}

CLINVAR_MISSENSE_PATTERN = re.compile(r"\(p\.([A-Za-z]{3})(\d+)([A-Za-z]{3})\)$")
BRCA_EXCHANGE_PROTEIN_PATTERN = re.compile(r":p\.\(?([A-Za-z]{3})(\d+)([A-Za-z]{3})\)?$")
PLAIN_HGVS_PROTEIN_PATTERN = re.compile(r"^p\.([A-Za-z]{3})(\d+)([A-Za-z]{3})$")
ONE_LETTER_PROTEIN_PATTERN = re.compile(r"^([A-Z])(\d+)([A-Z])$")
BRCA_RELEASE_DATE_PATTERN = re.compile(r"release-(\d{2})-(\d{2})-(\d{2})", flags=re.IGNORECASE)
GNOMAD_API_URL = "https://gnomad.broadinstitute.org/api"
GNOMAD_DEFAULT_DATASET = "gnomad_r4"
GNOMAD_DEFAULT_REFERENCE_GENOME = "GRCh38"
GNOMAD_QUERY_DELAY_SECONDS = 1.0


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _file_fingerprint(path: str | None) -> dict | None:
    if not path:
        return None
    candidate = Path(path)
    if not candidate.exists() or not candidate.is_file():
        return None
    stat = candidate.stat()
    digest = hashlib.sha256()
    with candidate.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            if not chunk:
                break
            digest.update(chunk)
    return {
        "path": str(candidate.resolve()),
        "size_bytes": int(stat.st_size),
        "sha256": digest.hexdigest(),
        "modified_at_epoch": float(stat.st_mtime),
    }


def _artifact_fingerprints(paths: dict[str, str | None]) -> dict[str, dict]:
    fingerprints: dict[str, dict] = {}
    for label, path in paths.items():
        fingerprint = _file_fingerprint(path)
        if fingerprint is not None:
            fingerprints[str(label)] = fingerprint
    return fingerprints


def _jsonify(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonify(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonify(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonify(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, np.bool_):
        return bool(value)
    if pd.isna(value):
        return None
    return value


def _render_markdown_html(markdown: str, title: str) -> str:
    blocks: list[str] = []
    for chunk in markdown.split("\n\n"):
        stripped = chunk.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            blocks.append(f"<h1>{html.escape(stripped[2:])}</h1>")
            continue
        if stripped.startswith("## "):
            blocks.append(f"<h2>{html.escape(stripped[3:])}</h2>")
            continue
        if stripped.startswith("- "):
            items = "".join(
                f"<li>{html.escape(line[2:])}</li>"
                for line in stripped.splitlines()
                if line.startswith("- ")
            )
            blocks.append(f"<ul>{items}</ul>")
            continue
        blocks.append(f"<p>{html.escape(stripped)}</p>")
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f7f1e8;color:#17242f;max-width:980px;margin:0 auto;padding:32px;line-height:1.65;}"
        "h1{font-size:2rem;margin-bottom:0.4rem;}h2{margin-top:2rem;color:#2d6f73;}ul{padding-left:1.2rem;}"
        "code{background:#efe4cf;padding:0.15rem 0.35rem;border-radius:4px;}"
        "</style></head><body>"
        + "".join(blocks)
        + "</body></html>"
    )


def _normalize_label(value: Any) -> str | None:
    return ALLOWED_LABELS.get(str(value or "").strip().lower())


def _label_group(value: str | None) -> str | None:
    if value in POSITIVE_LABELS:
        return "positive"
    if value in NEGATIVE_LABELS:
        return "negative"
    return None


def _review_status_rank(value: Any) -> int:
    text = str(value or "").strip().lower()
    if "practice guideline" in text:
        return 5
    if "expert panel" in text:
        return 4
    if "multiple submitters" in text and "no conflicts" in text:
        return 3
    if "multiple submitters" in text:
        return 2
    if "single submitter" in text:
        return 1
    return 0


def _finalize_hgvs_protein(ref: str, pos: str, alt: str) -> str | None:
    if ref not in AA3_CODES or alt not in AA3_CODES or ref == alt:
        return None
    return f"p.{ref}{pos}{alt}"


def _extract_clinvar_hgvs_protein(value: Any) -> str | None:
    match = CLINVAR_MISSENSE_PATTERN.search(str(value or "").strip())
    if not match:
        return None
    return _finalize_hgvs_protein(*match.groups())


def _extract_brca_exchange_hgvs_protein(value: Any) -> str | None:
    match = BRCA_EXCHANGE_PROTEIN_PATTERN.search(str(value or "").strip())
    if not match:
        return None
    return _finalize_hgvs_protein(*match.groups())


def _extract_plain_hgvs_protein(value: Any) -> str | None:
    match = PLAIN_HGVS_PROTEIN_PATTERN.match(str(value or "").strip())
    if not match:
        return None
    return _finalize_hgvs_protein(*match.groups())


def _extract_one_letter_hgvs_protein(value: Any) -> str | None:
    match = ONE_LETTER_PROTEIN_PATTERN.match(str(value or "").strip())
    if not match:
        return None
    ref, pos, alt = match.groups()
    if ref == alt or ref not in AA1_TO_AA3 or alt not in AA1_TO_AA3:
        return None
    return f"p.{AA1_TO_AA3[ref]}{pos}{AA1_TO_AA3[alt]}"


def _resolve_label_conflicts(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    if df.empty:
        return df.copy(), 0
    work = df.copy()
    work["label_group"] = work["label"].apply(_label_group)
    grouped = work.groupby(["gene", "hgvs_p"])["label_group"].nunique(dropna=True)
    conflict_pairs = set(grouped[grouped > 1].index.tolist())
    if not conflict_pairs:
        return work.drop(columns=["label_group"]), 0
    filtered = work[
        ~work.apply(lambda row: (row["gene"], row["hgvs_p"]) in conflict_pairs, axis=1)
    ].copy()
    return filtered.drop(columns=["label_group"]), int(len(conflict_pairs))


def _coerce_numeric(value: Any) -> float | None:
    if value in (None, "", "-", "NA", "na"):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _pick_first_numeric(row: pd.Series, names: Iterable[str]) -> float | None:
    for name in names:
        if name in row.index:
            value = _coerce_numeric(row[name])
            if value is not None:
                return value
    return None


def _pick_max_numeric(row: pd.Series, names: Iterable[str]) -> float | None:
    values = []
    for name in names:
        if name in row.index:
            value = _coerce_numeric(row[name])
            if value is not None:
                values.append(value)
    return max(values) if values else None


def _load_table(path: Path) -> pd.DataFrame:
    suffixes = [part.lower() for part in path.suffixes]
    if suffixes[-2:] == [".txt", ".gz"] or suffixes[-2:] == [".tsv", ".gz"]:
        return pd.read_csv(path, sep="\t", compression="gzip", low_memory=False)
    if suffixes[-2:] == [".csv", ".gz"]:
        return pd.read_csv(path, compression="gzip", low_memory=False)
    if path.suffix.lower() in {".tsv", ".txt"}:
        return pd.read_csv(path, sep="\t", low_memory=False)
    return pd.read_csv(path, low_memory=False)


def _parse_brca_exchange_release_date(path: Path) -> str:
    match = BRCA_RELEASE_DATE_PATTERN.search(path.name)
    if not match:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).date().isoformat()
    month, day, year = match.groups()
    return f"20{year}-{month}-{day}"


def _plain_hgvs_from_value(value: Any) -> str | None:
    raw = str(value or "").strip()
    if not raw or raw == "-":
        return None
    if raw.startswith("p.(") and raw.endswith(")"):
        raw = f"p.{raw[3:-1]}"
    if raw.startswith("(") and raw.endswith(")"):
        raw = raw[1:-1]
    return (
        _extract_plain_hgvs_protein(raw)
        or _extract_brca_exchange_hgvs_protein(raw)
        or _extract_one_letter_hgvs_protein(raw)
    )


def _extract_any_hgvs_protein(value: Any) -> str | None:
    raw = str(value or "").strip()
    if not raw or raw == "-":
        return None
    return (
        _extract_clinvar_hgvs_protein(raw)
        or _plain_hgvs_from_value(raw)
        or _plain_hgvs_from_value(raw.replace("(", "").replace(")", ""))
    )


def _pick_first_text(row: pd.Series, names: Iterable[str]) -> str | None:
    for name in names:
        if name in row.index:
            value = row[name]
            if pd.isna(value):
                continue
            text = str(value).strip()
            if text and text != "-":
                return text
    return None


def _relative_posix(path: Path, workspace_root: Path) -> str:
    return path.resolve().relative_to(workspace_root.resolve()).as_posix()


def _release_stem(path: Path) -> str:
    lowered = path.name.lower()
    if lowered.endswith(".tar.gz"):
        return path.name[:-7]
    if lowered.endswith(".txt.gz") or lowered.endswith(".tsv.gz") or lowered.endswith(".csv.gz"):
        return path.name[:-3]
    return path.stem


def _load_brca_exchange_variants(release_path: Path) -> pd.DataFrame:
    with tarfile.open(release_path, "r:*") as archive:
        candidate = next(
            (member for member in archive.getmembers() if member.name.endswith("output/variants_output.tsv")),
            None,
        )
        if candidate is None:
            raise FileNotFoundError("Arquivo output/variants_output.tsv nao encontrado no release do BRCA Exchange.")
        extracted = archive.extractfile(candidate)
        if extracted is None:
            raise FileNotFoundError("Nao foi possivel extrair output/variants_output.tsv do release do BRCA Exchange.")
        with TextIOWrapper(extracted, encoding="utf-8") as handle:
            return pd.read_csv(handle, sep="\t", low_memory=False)


def _prepare_clinvar_training(variant_summary_path: Path) -> tuple[pd.DataFrame, dict]:
    candidate_columns = {
        "GeneSymbol",
        "Gene",
        "gene",
        "gene_symbol",
        "Protein change",
        "protein_change",
        "HGVS_p",
        "protein",
        "ClinicalSignificance",
        "clinical_significance",
        "label",
        "ReviewStatus",
        "review_status",
        "VariationID",
        "variation_id",
        "AlleleID",
        "allele_id",
        "Name",
        "name",
        "LastEvaluated",
        "last_evaluated",
        "DateLastEvaluated",
    }
    suffixes = [part.lower() for part in variant_summary_path.suffixes]
    read_kwargs = {
        "sep": "\t",
        "low_memory": False,
        "usecols": lambda column_name: str(column_name) in candidate_columns,
        "chunksize": 50000,
    }
    if suffixes[-2:] == [".txt", ".gz"] or suffixes[-2:] == [".tsv", ".gz"]:
        reader = pd.read_csv(variant_summary_path, compression="gzip", **read_kwargs)
    else:
        reader = pd.read_csv(variant_summary_path, **read_kwargs)

    raw_rows = 0
    selected_frames: list[pd.DataFrame] = []
    for raw_chunk in reader:
        raw_rows += int(len(raw_chunk))
        work = raw_chunk.copy()

        gene_series = None
        for column in ["GeneSymbol", "Gene", "gene", "gene_symbol"]:
            if column in work.columns:
                current = work[column].astype("string")
                gene_series = current if gene_series is None else gene_series.fillna(current)
        work["gene"] = gene_series.str.upper() if gene_series is not None else pd.Series(dtype="string")

        hgvs_series = None
        for column in ["Protein change", "protein_change", "HGVS_p", "protein", "Name", "name"]:
            if column in work.columns:
                extracted = work[column].map(_extract_any_hgvs_protein)
                hgvs_series = extracted if hgvs_series is None else hgvs_series.fillna(extracted)
        work["hgvs_p"] = hgvs_series

        label_series = None
        for column in ["ClinicalSignificance", "clinical_significance", "label"]:
            if column in work.columns:
                current = work[column].map(_normalize_label)
                label_series = current if label_series is None else label_series.fillna(current)
        work["label"] = label_series

        review_series = None
        for column in ["ReviewStatus", "review_status"]:
            if column in work.columns:
                current = work[column].astype("string")
                review_series = current if review_series is None else review_series.fillna(current)
        work["review_status"] = review_series.fillna("ClinVar") if review_series is not None else "ClinVar"
        work["review_rank"] = work["review_status"].map(_review_status_rank)

        variant_id_series = None
        for column in ["VariationID", "variation_id", "AlleleID", "allele_id"]:
            if column in work.columns:
                current = work[column].astype("string")
                variant_id_series = current if variant_id_series is None else variant_id_series.fillna(current)
        work["variant_id"] = variant_id_series

        variant_name_series = None
        for column in ["Name", "name"]:
            if column in work.columns:
                current = work[column].astype("string")
                variant_name_series = current if variant_name_series is None else variant_name_series.fillna(current)
        work["variant_name"] = variant_name_series

        last_evaluated_series = None
        for column in ["LastEvaluated", "last_evaluated", "DateLastEvaluated"]:
            if column in work.columns:
                current = work[column].astype("string")
                last_evaluated_series = (
                    current if last_evaluated_series is None else last_evaluated_series.fillna(current)
                )
        work["last_evaluated"] = last_evaluated_series

        selected_chunk = work[
            work["gene"].isin(ALLOWED_GENES)
            & work["hgvs_p"].notna()
            & work["label"].notna()
        ].copy()
        if not selected_chunk.empty:
            selected_frames.append(
                selected_chunk[
                    [
                        "gene",
                        "hgvs_p",
                        "label",
                        "review_status",
                        "review_rank",
                        "variant_id",
                        "variant_name",
                        "last_evaluated",
                    ]
                ]
            )

    selected = (
        pd.concat(selected_frames, ignore_index=True)
        if selected_frames
        else pd.DataFrame(
            columns=[
                "gene",
                "hgvs_p",
                "label",
                "review_status",
                "review_rank",
                "variant_id",
                "variant_name",
                "last_evaluated",
            ]
        )
    )
    selected, conflict_pairs = _resolve_label_conflicts(
        selected
    )
    selected["last_evaluated_sort"] = pd.to_datetime(selected["last_evaluated"], errors="coerce")
    selected = selected.sort_values(
        by=["gene", "hgvs_p", "review_rank", "last_evaluated_sort", "variant_id"],
        ascending=[True, True, False, False, False],
        kind="stable",
    )
    deduplicated = selected.drop_duplicates(subset=["gene", "hgvs_p"], keep="first").copy()
    deduplicated["variant_name"] = deduplicated.apply(
        lambda row: row["variant_name"] or f"{row['gene']}:{row['hgvs_p']}",
        axis=1,
    )
    output = pd.DataFrame(
        {
            "GeneSymbol": deduplicated["gene"],
            "Protein change": deduplicated["hgvs_p"],
            "ClinicalSignificance": deduplicated["label"],
            "ReviewStatus": deduplicated["review_status"],
            "VariationID": deduplicated["variant_id"],
            "Name": deduplicated["variant_name"],
            "LastEvaluated": deduplicated["last_evaluated"],
        }
    ).reset_index(drop=True)
    return output, {
        "input_path": str(variant_summary_path.resolve()),
        "raw_rows": int(raw_rows),
        "selected_rows": int(len(selected)),
        "output_rows": int(len(output)),
        "conflicting_pairs_removed": int(conflict_pairs),
    }


def _prepare_clinvar_training_with_expert_holdout(
    variant_summary_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    full_df, summary = _prepare_clinvar_training(variant_summary_path)
    review_text = full_df["ReviewStatus"].fillna("").astype(str)
    expert_mask = review_text.str.contains("expert panel|practice guideline", case=False, na=False)
    expert_df = full_df.loc[expert_mask].copy().reset_index(drop=True)
    training_df = full_df.loc[~expert_mask].copy().reset_index(drop=True)

    # Keep the pipeline usable even for tiny synthetic fixtures.
    if training_df.empty:
        training_df = full_df.copy().reset_index(drop=True)
        expert_df = full_df.iloc[0:0].copy().reset_index(drop=True)

    expert_brca1 = expert_df[expert_df["GeneSymbol"].astype(str) == "BRCA1"].copy()
    expert_brca2 = expert_df[expert_df["GeneSymbol"].astype(str) == "BRCA2"].copy()
    summary = {
        **summary,
        "full_output_rows": int(len(full_df)),
        "training_output_rows": int(len(training_df)),
        "expert_holdout_rows": int(len(expert_df)),
        "expert_holdout_brca1_rows": int(len(expert_brca1)),
        "expert_holdout_brca2_rows": int(len(expert_brca2)),
    }
    return training_df, expert_df, summary


def _prepare_direct_gnomad_annotations_from_file(
    gnomad_path: Path,
    *,
    release_label: str | None = None,
) -> tuple[pd.DataFrame, dict]:
    raw = _load_table(gnomad_path)
    work = raw.copy()
    work["gene"] = work.apply(
        lambda row: _pick_first_text(row, ["gene", "gene_symbol", "Gene", "symbol"]),
        axis=1,
    )
    work["gene"] = work["gene"].astype(str).str.upper().where(work["gene"].notna(), None)
    work["hgvs_p"] = work.apply(
        lambda row: _extract_any_hgvs_protein(
            _pick_first_text(row, ["hgvs_p", "hgvsp", "HGVSp", "hgvs_pro", "protein_change"])
        ),
        axis=1,
    )
    work["af"] = work.apply(
        lambda row: _pick_first_numeric(row, ["af", "AF", "joint_af", "genome_af", "feature_gnomad_af"]),
        axis=1,
    )
    work["ac"] = work.apply(
        lambda row: _pick_first_numeric(row, ["ac", "AC", "feature_gnomad_ac"]),
        axis=1,
    )
    work["an"] = work.apply(
        lambda row: _pick_first_numeric(row, ["an", "AN", "feature_gnomad_an"]),
        axis=1,
    )
    work["popmax_af"] = work.apply(
        lambda row: _pick_first_numeric(
            row,
            ["popmax_af", "AF_popmax", "faf95_popmax", "feature_gnomad_popmax_af"],
        ),
        axis=1,
    )
    work = work[work["gene"].isin(ALLOWED_GENES) & work["hgvs_p"].notna()].copy()
    work["meta_brca_exchange_release"] = release_label or _release_stem(gnomad_path)
    output = (
        work.groupby(["gene", "hgvs_p"], dropna=False, as_index=False)
        .agg(
            {
                "af": "max",
                "ac": "max",
                "an": "max",
                "popmax_af": "max",
                "meta_brca_exchange_release": "first",
            }
        )
        .reset_index(drop=True)
    )
    return output, {
        "input_path": str(gnomad_path.resolve()),
        "raw_rows": int(len(raw)),
        "output_rows": int(len(output)),
        "release_value": release_label or _release_stem(gnomad_path),
    }


def _gnomad_query_text(*, gene_symbol: str, dataset_id: str, reference_genome: str) -> str:
    return "\n".join(
        [
            "{",
            f'  gene(gene_symbol: "{gene_symbol}", reference_genome: {reference_genome}) {{',
            f"    variants(dataset: {dataset_id}) {{",
            "      variant_id",
            "      hgvsp",
            "      transcript_consequence {",
            "        gene_symbol",
            "        hgvsp",
            "        major_consequence",
            "        is_canonical",
            "        transcript_id",
            "      }",
            "      exome {",
            "        ac",
            "        an",
            "        af",
            "        populations {",
            "          id",
            "          ac",
            "          an",
            "        }",
            "      }",
            "      genome {",
            "        ac",
            "        an",
            "        af",
            "        populations {",
            "          id",
            "          ac",
            "          an",
            "        }",
            "      }",
            "      joint {",
            "        ac",
            "        an",
            "        fafmax {",
            "          faf95_max",
            "        }",
            "      }",
            "    }",
            "  }",
            "}",
        ]
    )


def _gnomad_graphql_post(query: str) -> dict:
    payload = json.dumps({"query": query}).encode("utf-8")
    request = urllib.request.Request(
        GNOMAD_API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            decoded = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:  # pragma: no cover - exercised in integration flows
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Falha ao consultar a API do gnomAD: HTTP {exc.code} - {details}") from exc
    except urllib.error.URLError as exc:  # pragma: no cover - exercised in integration flows
        raise RuntimeError(f"Falha de rede ao consultar a API do gnomAD: {exc.reason}") from exc

    data = json.loads(decoded)
    if data.get("errors"):
        raise RuntimeError(f"API do gnomAD retornou erro: {json.dumps(data['errors'], ensure_ascii=False)}")
    return data


def _population_popmax(populations: Any) -> float | None:
    if not isinstance(populations, list):
        return None
    values: list[float] = []
    for entry in populations:
        if not isinstance(entry, dict):
            continue
        ac = _coerce_numeric(entry.get("ac"))
        an = _coerce_numeric(entry.get("an"))
        if ac is None or an in (None, 0):
            continue
        values.append(float(ac) / float(an))
    return max(values) if values else None


def _pick_joint_frequency(variant: dict) -> tuple[float | None, float | None, float | None]:
    exome = variant.get("exome") or {}
    genome = variant.get("genome") or {}
    joint = variant.get("joint") or {}

    joint_ac = _coerce_numeric(joint.get("ac"))
    joint_an = _coerce_numeric(joint.get("an"))
    if joint_ac is not None and joint_an not in (None, 0):
        return float(joint_ac), float(joint_an), float(joint_ac) / float(joint_an)

    exome_ac = _coerce_numeric(exome.get("ac")) or 0.0
    exome_an = _coerce_numeric(exome.get("an")) or 0.0
    genome_ac = _coerce_numeric(genome.get("ac")) or 0.0
    genome_an = _coerce_numeric(genome.get("an")) or 0.0
    total_an = exome_an + genome_an
    total_ac = exome_ac + genome_ac
    if total_an > 0:
        return float(total_ac), float(total_an), float(total_ac) / float(total_an)

    af_candidates = [_coerce_numeric(exome.get("af")), _coerce_numeric(genome.get("af"))]
    af_candidates = [float(item) for item in af_candidates if item is not None]
    if af_candidates:
        return None, None, max(af_candidates)
    return None, None, None


def _prepare_direct_gnomad_annotations_from_api(
    *,
    dataset_id: str = GNOMAD_DEFAULT_DATASET,
    reference_genome: str = GNOMAD_DEFAULT_REFERENCE_GENOME,
) -> tuple[pd.DataFrame, dict]:
    rows: list[dict] = []
    raw_variant_rows = 0
    missense_rows = 0
    query_genes = sorted(ALLOWED_GENES)

    for index, gene_symbol in enumerate(query_genes):
        query = _gnomad_query_text(
            gene_symbol=gene_symbol,
            dataset_id=dataset_id,
            reference_genome=reference_genome,
        )
        payload = _gnomad_graphql_post(query)
        variants = (((payload.get("data") or {}).get("gene") or {}).get("variants")) or []
        raw_variant_rows += int(len(variants))
        for variant in variants:
            transcript_consequence = variant.get("transcript_consequence") or {}
            consequence = str(transcript_consequence.get("major_consequence") or "").strip().lower()
            hgvs_p = _extract_any_hgvs_protein(
                transcript_consequence.get("hgvsp") or variant.get("hgvsp")
            )
            resolved_gene = str(transcript_consequence.get("gene_symbol") or gene_symbol).strip().upper()
            if consequence != "missense_variant" or resolved_gene not in ALLOWED_GENES or not hgvs_p:
                continue
            missense_rows += 1
            ac, an, af = _pick_joint_frequency(variant)
            exome = variant.get("exome") or {}
            genome = variant.get("genome") or {}
            joint = variant.get("joint") or {}
            popmax_candidates = [
                _population_popmax(exome.get("populations")),
                _population_popmax(genome.get("populations")),
                _coerce_numeric(((joint.get("fafmax") or {}).get("faf95_max"))),
            ]
            popmax_candidates = [float(item) for item in popmax_candidates if item is not None]
            rows.append(
                {
                    "gene": resolved_gene,
                    "hgvs_p": hgvs_p,
                    "af": af,
                    "ac": ac,
                    "an": an,
                    "popmax_af": max(popmax_candidates) if popmax_candidates else None,
                    "meta_gnomad_variant_id": variant.get("variant_id"),
                    "meta_gnomad_transcript_id": transcript_consequence.get("transcript_id"),
                    "meta_gnomad_consequence": consequence,
                    "meta_gnomad_dataset": dataset_id,
                    "meta_gnomad_reference_genome": reference_genome,
                }
            )
        if index < len(query_genes) - 1:
            time.sleep(GNOMAD_QUERY_DELAY_SECONDS)

    output = pd.DataFrame(rows)
    if output.empty:
        output = pd.DataFrame(
            columns=[
                "gene",
                "hgvs_p",
                "af",
                "ac",
                "an",
                "popmax_af",
                "meta_gnomad_variant_id",
                "meta_gnomad_transcript_id",
                "meta_gnomad_consequence",
                "meta_gnomad_dataset",
                "meta_gnomad_reference_genome",
            ]
        )
    else:
        output = (
            output.groupby(["gene", "hgvs_p"], dropna=False, as_index=False)
            .agg(
                {
                    "af": "max",
                    "ac": "max",
                    "an": "max",
                    "popmax_af": "max",
                    "meta_gnomad_variant_id": "first",
                    "meta_gnomad_transcript_id": "first",
                    "meta_gnomad_consequence": "first",
                    "meta_gnomad_dataset": "first",
                    "meta_gnomad_reference_genome": "first",
                }
            )
            .sort_values(["gene", "hgvs_p"], ascending=[True, True], kind="stable")
            .reset_index(drop=True)
        )

    return output, {
        "source_mode": "direct_api",
        "api_endpoint": GNOMAD_API_URL,
        "dataset_id": dataset_id,
        "reference_genome": reference_genome,
        "query_genes": query_genes,
        "query_count": int(len(query_genes)),
        "query_delay_seconds": float(GNOMAD_QUERY_DELAY_SECONDS),
        "release_value": f"{dataset_id}_graphql_{datetime.now(timezone.utc).date().isoformat()}",
        "raw_rows": int(raw_variant_rows),
        "missense_rows": int(missense_rows),
        "output_rows": int(len(output)),
    }


def _prepare_brca_exchange_tables(
    release_path: Path,
    *,
    training_pairs: set[tuple[str, str]],
    direct_gnomad_path: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    raw = _load_brca_exchange_variants(release_path)
    release_date = _parse_brca_exchange_release_date(release_path)
    release_label = _release_stem(release_path)

    work = raw.copy()
    work["gene"] = work.apply(
        lambda row: _pick_first_text(
            row,
            ["gene_symbol", "Gene_symbol_ENIGMA", "GeneSymbol", "gene"],
        ),
        axis=1,
    )
    work["gene"] = work["gene"].astype(str).str.upper().where(work["gene"].notna(), None)
    work["hgvs_p"] = None
    for column in [
        "protein",
        "Protein change",
        "HGVS_protein_ENIGMA",
        "HGVS_protein_LOVD",
        "Protein_ClinVar",
        "HGVS_protein_exLOVD",
        "Abbrev_AA_change_ENIGMA",
    ]:
        if column in work.columns:
            extracted = work[column].apply(_extract_any_hgvs_protein)
            work["hgvs_p"] = work["hgvs_p"].fillna(extracted)

    work["variant_id"] = work.apply(
        lambda row: _pick_first_text(row, ["ca_id", "CA_ID", "BX_ID_ENIGMA", "BX_ID_LOVD", "BX_ID_ClinVar"]),
        axis=1,
    )
    work["variant_name"] = work.apply(
        lambda row: _pick_first_text(
            row,
            [
                "HGVS_protein_LOVD",
                "HGVS_protein_ENIGMA",
                "Protein_ClinVar",
                "protein",
                "genomic_hgvs_38",
                "Genomic_Coordinate",
            ],
        ),
        axis=1,
    )
    work["lovd_label"] = work.apply(
        lambda row: _normalize_label(_pick_first_text(row, ["classification_lovd", "Classification_LOVD"])),
        axis=1,
    )
    work["enigma_label"] = work.apply(
        lambda row: _normalize_label(
            _pick_first_text(row, ["clinical_significance_enigma", "Clinical_significance_ENIGMA"])
        ),
        axis=1,
    )
    work["source_tag"] = work.apply(lambda row: _pick_first_text(row, ["source", "Source"]) or "", axis=1)
    work = work[work["gene"].isin(ALLOWED_GENES) & work["hgvs_p"].notna()].copy()

    enigma = work[work["enigma_label"].notna()].copy()
    enigma = enigma[["gene", "hgvs_p", "enigma_label", "variant_id"]].rename(columns={"enigma_label": "label"})
    enigma, enigma_conflicts = _resolve_label_conflicts(enigma)
    enigma = enigma.sort_values(by=["gene", "hgvs_p", "variant_id"], kind="stable")
    enigma = enigma.drop_duplicates(subset=["gene", "hgvs_p"], keep="first").copy()
    enigma_output = pd.DataFrame(
        {
            "gene": enigma["gene"],
            "hgvs_p": enigma["hgvs_p"],
            "label": enigma["label"],
            "variant_id": enigma["variant_id"],
            "review_status": f"ENIGMA/BRCA Exchange curated release {release_date}",
            "source": "BRCA Exchange / ENIGMA",
        }
    ).reset_index(drop=True)

    lovd = work[work["lovd_label"].notna()].copy()
    if "source_tag" in lovd.columns:
        lovd = lovd[
            lovd["source_tag"].astype(str).str.contains("lovd", case=False, na=False) | lovd["lovd_label"].notna()
        ].copy()
    lovd = lovd[
        ~lovd.apply(lambda row: (str(row["gene"]), str(row["hgvs_p"])) in training_pairs, axis=1)
    ].copy()
    enigma_lookup = enigma_output[["gene", "hgvs_p", "label"]].rename(columns={"label": "meta_enigma_label"})
    lovd = lovd.merge(enigma_lookup, on=["gene", "hgvs_p"], how="left")
    lovd = lovd[["gene", "hgvs_p", "lovd_label", "variant_id", "variant_name", "meta_enigma_label"]].rename(
        columns={"lovd_label": "label"}
    )
    lovd, lovd_conflicts = _resolve_label_conflicts(lovd)
    lovd = lovd.sort_values(by=["gene", "hgvs_p", "variant_id"], kind="stable")
    lovd = lovd.drop_duplicates(subset=["gene", "hgvs_p"], keep="first").copy()
    lovd["variant_name"] = lovd.apply(
        lambda row: row["variant_name"] or row["hgvs_p"],
        axis=1,
    )
    lovd_output = pd.DataFrame(
        {
            "GeneSymbol": lovd["gene"],
            "Protein change": lovd["hgvs_p"],
            "ClinicalSignificance": lovd["label"],
            "ReviewStatus": f"BRCA Exchange / LOVD external curated release {release_date}",
            "VariationID": lovd["variant_id"],
            "Name": lovd["variant_name"],
            "meta_enigma_label": lovd["meta_enigma_label"],
        }
    ).reset_index(drop=True)

    if direct_gnomad_path is not None:
        gnomad_output, gnomad_summary = _prepare_direct_gnomad_annotations_from_file(
            direct_gnomad_path,
            release_label=release_label,
        )
        gnomad_summary["source_mode"] = "direct_file"
    else:
        gnomad_output, gnomad_summary = _prepare_direct_gnomad_annotations_from_api()

    return lovd_output, enigma_output, gnomad_output, {
        "input_path": str(release_path.resolve()),
        "release_date": release_date,
        "release_value": release_label,
        "raw_rows": int(len(raw)),
        "lovd_output_rows": int(len(lovd_output)),
        "enigma_output_rows": int(len(enigma_output)),
        "lovd_conflicting_pairs_removed": int(lovd_conflicts),
        "enigma_conflicting_pairs_removed": int(enigma_conflicts),
        "training_overlap_removed": int(
            work[work["lovd_label"].notna()].apply(
                lambda row: (str(row["gene"]), str(row["hgvs_p"])) in training_pairs,
                axis=1,
            ).sum()
        ),
        "gnomad_summary": gnomad_summary,
    }


def _iter_mavedb_score_sets(metadata: dict) -> list[dict]:
    score_sets: list[dict] = []
    for experiment_set in metadata.get("experimentSets", []):
        experiments = experiment_set.get("experiments") or []
        for experiment in experiments:
            experiment_title = str(experiment.get("title") or experiment.get("shortDescription") or "")
            experiment_targets = [
                str(target.get("name") or target.get("mappedHgncName") or "").upper()
                for target in (experiment.get("targetGenes") or [])
                if str(target.get("name") or target.get("mappedHgncName") or "").strip()
            ]
            for score_set in experiment.get("scoreSets") or []:
                target_genes = [
                    str(target.get("name") or target.get("mappedHgncName") or "").upper()
                    for target in (score_set.get("targetGenes") or [])
                    if str(target.get("name") or target.get("mappedHgncName") or "").strip()
                ]
                if not target_genes:
                    target_genes = list(experiment_targets)
                assay_name = str(score_set.get("title") or experiment_title or score_set.get("urn") or "").strip()
                score_sets.append(
                    {
                        "urn": str(score_set.get("urn") or "").strip(),
                        "assay_name": assay_name,
                        "target_genes": target_genes,
                        "processing_state": str(score_set.get("processingState") or ""),
                    }
                )
    return score_sets


def _prepare_mavedb_scores(mavedb_dump_path: Path) -> tuple[pd.DataFrame, dict]:
    with zipfile.ZipFile(mavedb_dump_path) as archive:
        with archive.open("main.json") as handle:
            metadata = json.load(handle)
        score_sets = _iter_mavedb_score_sets(metadata)
        selected = [
            item
            for item in score_sets
            if item["urn"]
            and any(gene in ALLOWED_GENES for gene in item["target_genes"])
            and item["processing_state"].lower() != "failed"
        ]
        frames: list[pd.DataFrame] = []
        missing_entries: list[str] = []
        for item in selected:
            gene = next((token for token in item["target_genes"] if token in ALLOWED_GENES), None)
            if not gene:
                continue
            entry_name = f"csv/{item['urn'].replace(':', '-')}.scores.csv"
            if entry_name not in archive.namelist():
                missing_entries.append(entry_name)
                continue
            with archive.open(entry_name) as handle:
                frame = pd.read_csv(handle, low_memory=False)
            hgvs_series = frame.apply(
                lambda row: _extract_any_hgvs_protein(
                    _pick_first_text(row, ["hgvs_pro", "hgvsPro", "hgvs_p", "protein_variant"])
                ),
                axis=1,
            )
            score_frame = pd.DataFrame(
                {
                    "gene": gene,
                    "hgvs_p": hgvs_series,
                    "score": frame.apply(
                        lambda row: _pick_first_numeric(row, ["score", "functional_score", "score_value"]),
                        axis=1,
                    ),
                    "score_se": frame.apply(
                        lambda row: _pick_first_numeric(row, ["score_se", "se", "standard_error"]),
                        axis=1,
                    ),
                    "score_set_urn": item["urn"],
                    "assay_name": item["assay_name"],
                }
            )
            score_frame = score_frame[score_frame["hgvs_p"].notna() & score_frame["score"].notna()].copy()
            frames.append(score_frame)

    output = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(
        columns=["gene", "hgvs_p", "score", "score_se", "score_set_urn", "assay_name"]
    )
    output = output.drop_duplicates(subset=["gene", "hgvs_p", "score_set_urn"], keep="first").reset_index(drop=True)
    return output, {
        "input_path": str(mavedb_dump_path.resolve()),
        "release_value": _release_stem(mavedb_dump_path),
        "selected_score_sets": [item["urn"] for item in selected],
        "selected_score_set_count": int(len(selected)),
        "missing_score_csv_entries": missing_entries,
        "output_rows": int(len(output)),
    }


def _build_real_config_text(
    *,
    clinvar_release_date: str,
    gnomad_release_value: str,
    mavedb_release_value: str,
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
            'name = "clinvar_variant_summary"',
            'kind = "cohort"',
            'type = "file"',
            'format = "tsv"',
            f'path = "{_relative_posix(training_path, workspace_root)}"',
            'preset = "clinvar_variant_summary"',
            f'release_date = "{clinvar_release_date}"',
            "",
            "[[sources]]",
            'name = "gnomad_brca_annotations"',
            'kind = "annotation"',
            'type = "file"',
            'format = "tsv"',
            f'path = "{_relative_posix(gnomad_path, workspace_root)}"',
            'preset = "gnomad_variant_table"',
            'join_on = ["gene", "hgvs_p"]',
            f'release_version = "{gnomad_release_value}"',
            "",
            "[[sources]]",
            'name = "mavedb_brca_scores"',
            'kind = "annotation"',
            'type = "file"',
            'format = "csv"',
            f'path = "{_relative_posix(mavedb_path, workspace_root)}"',
            'preset = "mavedb_score_table"',
            'join_on = ["gene", "hgvs_p"]',
            f'release_version = "{mavedb_release_value}"',
            "",
        ]
    )


def _build_external_config_text(
    *,
    external_release_date: str,
    gnomad_release_value: str,
    mavedb_release_value: str,
    external_path: Path,
    gnomad_path: Path,
    mavedb_path: Path,
    workspace_root: Path,
    cohort_source_name: str = "bridges_like_validation",
) -> str:
    return "\n".join(
        [
            "[ingestion]",
            'deduplicate_on = ["gene", "hgvs_p", "label"]',
            "prefer_annotation_values = true",
            "",
            "[[sources]]",
            f'name = "{cohort_source_name}"',
            'kind = "cohort"',
            'type = "file"',
            'format = "tsv"',
            f'path = "{_relative_posix(external_path, workspace_root)}"',
            'preset = "clinvar_variant_summary"',
            f'release_date = "{external_release_date}"',
            "",
            "[[sources]]",
            'name = "gnomad_validation_annotations"',
            'kind = "annotation"',
            'type = "file"',
            'format = "tsv"',
            f'path = "{_relative_posix(gnomad_path, workspace_root)}"',
            'preset = "gnomad_variant_table"',
            'join_on = ["gene", "hgvs_p"]',
            f'release_version = "{gnomad_release_value}"',
            "",
            "[[sources]]",
            'name = "mavedb_validation_scores"',
            'kind = "annotation"',
            'type = "file"',
            'format = "csv"',
            f'path = "{_relative_posix(mavedb_path, workspace_root)}"',
            'preset = "mavedb_score_table"',
            'join_on = ["gene", "hgvs_p"]',
            f'release_version = "{mavedb_release_value}"',
            "",
        ]
    )


def _build_real_benchmark_text(
    *,
    train_config_path: Path,
    external_cohorts: list[tuple[str, Path]],
    workspace_root: Path,
) -> str:
    lines = [
        "[study]",
        'name = "Public BRCA Benchmark Real Data"',
        'mode = "hybrid"',
        "high_confidence_only = false",
        "keep_metadata = true",
        'primary_metric = "auc_roc"',
        'baseline_experiment = "external_predictors_only"',
        "n_bootstrap = 100",
        "",
        "[[cohorts]]",
        'name = "public_brca_training"',
        'role = "train"',
        f'source_config = "{_relative_posix(train_config_path, workspace_root)}"',
        "",
    ]
    for cohort_name, config_path in external_cohorts:
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


def _validate_prepared_artifact(path: Path, preset_name: str) -> dict:
    dataframe = _load_table(path)
    normalized = apply_source_preset(dataframe, preset_name)
    return {
        "path": str(path.resolve()),
        "preset": preset_name,
        "raw_rows": int(len(dataframe)),
        "normalized_rows": int(len(normalized)),
        "normalized_columns": [str(column) for column in normalized.columns],
    }


def _build_real_data_preparation_markdown(bundle: dict) -> str:
    summary = dict(bundle.get("summary") or {})
    training_summary = dict(bundle.get("training_summary") or {})
    brca_summary = dict(bundle.get("brca_exchange_summary") or {})
    gnomad_summary = dict(bundle.get("gnomad_summary") or {})
    mavedb_summary = dict(bundle.get("mavedb_summary") or {})
    artifact_paths = dict(bundle.get("artifact_paths") or {})
    config_paths = dict(bundle.get("config_paths") or {})

    lines = [
        "# PrimeVarClass Real-data Preparation",
        "",
        f"- Generated at: {summary.get('generated_at')}",
        f"- Workspace root: {summary.get('workspace_root')}",
        f"- ClinVar training variants: {summary.get('training_rows')}",
        f"- ClinVar expert external variants: {summary.get('clinvar_expert_rows')}",
        f"- ClinVar expert BRCA1 variants: {summary.get('clinvar_expert_brca1_rows')}",
        f"- ClinVar expert BRCA2 variants: {summary.get('clinvar_expert_brca2_rows')}",
        f"- BRCA Exchange LOVD external variants: {summary.get('external_rows')}",
        f"- BRCA1 external variants: {summary.get('external_brca1_rows')}",
        f"- BRCA2 external variants: {summary.get('external_brca2_rows')}",
        f"- ENIGMA curated missense variants: {summary.get('enigma_rows')}",
        f"- gnomAD-style annotation rows: {summary.get('gnomad_rows')}",
        f"- MaveDB function-score rows: {summary.get('mavedb_rows')}",
        "",
        "## Input provenance",
        "",
        f"- ClinVar input: {training_summary.get('input_path')}",
        f"- BRCA Exchange input: {brca_summary.get('input_path')}",
        f"- MaveDB input: {mavedb_summary.get('input_path')}",
        f"- gnomAD mode: {gnomad_summary.get('source_mode')}",
        "",
        "## Canonical artifacts",
        "",
    ]
    for label, path in artifact_paths.items():
        lines.append(f"- {label}: {path}")
    lines.extend(["", "## Study configs", ""])
    for label, path in config_paths.items():
        lines.append(f"- {label}: {path}")
    lines.extend(
        [
            "",
        "## Preparation notes",
        "",
        f"- ClinVar label conflicts removed: {training_summary.get('conflicting_pairs_removed')}",
        f"- ClinVar expert holdout rows: {training_summary.get('expert_holdout_rows')}",
        f"- BRCA Exchange LOVD overlaps removed against training cohort: {brca_summary.get('training_overlap_removed')}",
        f"- BRCA Exchange release value: {brca_summary.get('release_value')}",
        f"- gnomAD release value: {gnomad_summary.get('release_value')}",
        f"- gnomAD source mode: {gnomad_summary.get('source_mode')}",
        f"- MaveDB selected score sets: {mavedb_summary.get('selected_score_set_count')}",
        f"- Benchmark external cohorts: {summary.get('benchmark_external_cohort_count')}",
        "",
    ]
    )
    missing_entries = mavedb_summary.get("missing_score_csv_entries") or []
    if missing_entries:
        lines.append("## Missing MaveDB score tables")
        lines.append("")
        for entry in missing_entries:
            lines.append(f"- {entry}")
        lines.append("")
    return "\n".join(lines).strip()


def build_real_data_preparation_bundle(
    *,
    clinvar_variant_summary_path: str,
    brca_exchange_release_path: str,
    mavedb_dump_path: str,
    output_dir: str,
    workspace_root: str | None = None,
    gnomad_annotations_path: str | None = None,
) -> dict:
    root = Path(workspace_root).resolve() if workspace_root else Path(__file__).resolve().parents[2]
    clinvar_input = Path(clinvar_variant_summary_path).resolve()
    brca_input = Path(brca_exchange_release_path).resolve()
    mavedb_input = Path(mavedb_dump_path).resolve()
    gnomad_input = Path(gnomad_annotations_path).resolve() if gnomad_annotations_path else None

    training_output_path = root / "data" / "raw" / "clinvar" / "brca_missense_variant_summary.tsv"
    clinvar_expert_output_path = root / "data" / "raw" / "clinvar" / "brca_missense_expert_external.tsv"
    clinvar_expert_brca1_output_path = root / "data" / "raw" / "clinvar" / "brca_missense_expert_external_brca1.tsv"
    clinvar_expert_brca2_output_path = root / "data" / "raw" / "clinvar" / "brca_missense_expert_external_brca2.tsv"
    external_output_path = root / "data" / "raw" / "brca_exchange" / "brca_exchange_lovd_external.tsv"
    external_brca1_output_path = root / "data" / "raw" / "brca_exchange" / "brca_exchange_lovd_external_brca1.tsv"
    external_brca2_output_path = root / "data" / "raw" / "brca_exchange" / "brca_exchange_lovd_external_brca2.tsv"
    enigma_output_path = root / "data" / "raw" / "brca_exchange" / "enigma_brca_curated.tsv"
    gnomad_output_path = root / "data" / "raw" / "gnomad" / "brca_missense_annotations.tsv"
    mavedb_output_path = root / "data" / "raw" / "mavedb" / "brca_function_scores.csv"
    real_config_path = root / "configs" / "public_brca_real.toml"
    external_config_path = root / "configs" / "public_brca_external_real.toml"
    clinvar_expert_config_path = root / "configs" / "public_brca_external_real_clinvar_expert.toml"
    clinvar_expert_brca1_config_path = root / "configs" / "public_brca_external_real_clinvar_expert_brca1.toml"
    clinvar_expert_brca2_config_path = root / "configs" / "public_brca_external_real_clinvar_expert_brca2.toml"
    external_brca1_config_path = root / "configs" / "public_brca_external_real_brca1.toml"
    external_brca2_config_path = root / "configs" / "public_brca_external_real_brca2.toml"
    benchmark_config_path = root / "configs" / "public_brca_benchmark_real.toml"

    training_df, clinvar_expert_df, training_summary = _prepare_clinvar_training_with_expert_holdout(clinvar_input)
    clinvar_expert_brca1_df = clinvar_expert_df[clinvar_expert_df["GeneSymbol"].astype(str) == "BRCA1"].copy().reset_index(drop=True)
    clinvar_expert_brca2_df = clinvar_expert_df[clinvar_expert_df["GeneSymbol"].astype(str) == "BRCA2"].copy().reset_index(drop=True)
    training_pairs = {
        (str(row["GeneSymbol"]), str(row["Protein change"]))
        for row in training_df.to_dict(orient="records")
    }
    external_df, enigma_df, gnomad_df, brca_summary = _prepare_brca_exchange_tables(
        brca_input,
        training_pairs=training_pairs,
        direct_gnomad_path=gnomad_input,
    )
    external_brca1_df = external_df[external_df["GeneSymbol"].astype(str) == "BRCA1"].copy().reset_index(drop=True)
    external_brca2_df = external_df[external_df["GeneSymbol"].astype(str) == "BRCA2"].copy().reset_index(drop=True)
    mavedb_df, mavedb_summary = _prepare_mavedb_scores(mavedb_input)

    for path in [
        training_output_path.parent,
        external_output_path.parent,
        gnomad_output_path.parent,
        mavedb_output_path.parent,
        real_config_path.parent,
    ]:
        path.mkdir(parents=True, exist_ok=True)

    training_df.to_csv(training_output_path, sep="\t", index=False)
    clinvar_expert_df.to_csv(clinvar_expert_output_path, sep="\t", index=False)
    clinvar_expert_brca1_df.to_csv(clinvar_expert_brca1_output_path, sep="\t", index=False)
    clinvar_expert_brca2_df.to_csv(clinvar_expert_brca2_output_path, sep="\t", index=False)
    external_df.to_csv(external_output_path, sep="\t", index=False)
    external_brca1_df.to_csv(external_brca1_output_path, sep="\t", index=False)
    external_brca2_df.to_csv(external_brca2_output_path, sep="\t", index=False)
    enigma_df.to_csv(enigma_output_path, sep="\t", index=False)
    gnomad_df.to_csv(gnomad_output_path, sep="\t", index=False)
    mavedb_df.to_csv(mavedb_output_path, index=False)

    clinvar_release_date = datetime.fromtimestamp(clinvar_input.stat().st_mtime, tz=timezone.utc).date().isoformat()
    gnomad_release_value = str(
        (brca_summary.get("gnomad_summary") or {}).get("release_value")
        or (_release_stem(gnomad_input) if gnomad_input else f"{_release_stem(brca_input)}-derived-gnomad")
    )
    mavedb_release_value = str(mavedb_summary.get("release_value") or _release_stem(mavedb_input))
    external_release_date = str(brca_summary.get("release_date") or clinvar_release_date)

    real_config_path.write_text(
        _build_real_config_text(
            clinvar_release_date=clinvar_release_date,
            gnomad_release_value=gnomad_release_value,
            mavedb_release_value=mavedb_release_value,
            training_path=training_output_path,
            gnomad_path=gnomad_output_path,
            mavedb_path=mavedb_output_path,
            workspace_root=root,
        ),
        encoding="utf-8",
    )
    external_config_path.write_text(
        _build_external_config_text(
            external_release_date=external_release_date,
            gnomad_release_value=gnomad_release_value,
            mavedb_release_value=mavedb_release_value,
            external_path=external_output_path,
            gnomad_path=gnomad_output_path,
            mavedb_path=mavedb_output_path,
            workspace_root=root,
        ),
        encoding="utf-8",
    )
    clinvar_expert_config_path.write_text(
        _build_external_config_text(
            external_release_date=clinvar_release_date,
            gnomad_release_value=gnomad_release_value,
            mavedb_release_value=mavedb_release_value,
            external_path=clinvar_expert_output_path,
            gnomad_path=gnomad_output_path,
            mavedb_path=mavedb_output_path,
            workspace_root=root,
            cohort_source_name="clinvar_expert_validation",
        ),
        encoding="utf-8",
    )
    clinvar_expert_brca1_config_path.write_text(
        _build_external_config_text(
            external_release_date=clinvar_release_date,
            gnomad_release_value=gnomad_release_value,
            mavedb_release_value=mavedb_release_value,
            external_path=clinvar_expert_brca1_output_path,
            gnomad_path=gnomad_output_path,
            mavedb_path=mavedb_output_path,
            workspace_root=root,
            cohort_source_name="clinvar_expert_validation_brca1",
        ),
        encoding="utf-8",
    )
    clinvar_expert_brca2_config_path.write_text(
        _build_external_config_text(
            external_release_date=clinvar_release_date,
            gnomad_release_value=gnomad_release_value,
            mavedb_release_value=mavedb_release_value,
            external_path=clinvar_expert_brca2_output_path,
            gnomad_path=gnomad_output_path,
            mavedb_path=mavedb_output_path,
            workspace_root=root,
            cohort_source_name="clinvar_expert_validation_brca2",
        ),
        encoding="utf-8",
    )
    external_brca1_config_path.write_text(
        _build_external_config_text(
            external_release_date=external_release_date,
            gnomad_release_value=gnomad_release_value,
            mavedb_release_value=mavedb_release_value,
            external_path=external_brca1_output_path,
            gnomad_path=gnomad_output_path,
            mavedb_path=mavedb_output_path,
            workspace_root=root,
            cohort_source_name="bridges_like_validation_brca1",
        ),
        encoding="utf-8",
    )
    external_brca2_config_path.write_text(
        _build_external_config_text(
            external_release_date=external_release_date,
            gnomad_release_value=gnomad_release_value,
            mavedb_release_value=mavedb_release_value,
            external_path=external_brca2_output_path,
            gnomad_path=gnomad_output_path,
            mavedb_path=mavedb_output_path,
            workspace_root=root,
            cohort_source_name="bridges_like_validation_brca2",
        ),
        encoding="utf-8",
    )
    benchmark_config_path.write_text(
        _build_real_benchmark_text(
            train_config_path=real_config_path,
            external_cohorts=[
                (name, config_path)
                for name, config_path, size in [
                    ("clinvar_expert_external_validation_brca1", clinvar_expert_brca1_config_path, len(clinvar_expert_brca1_df)),
                    ("clinvar_expert_external_validation_brca2", clinvar_expert_brca2_config_path, len(clinvar_expert_brca2_df)),
                    ("bridges_like_external_validation_brca1", external_brca1_config_path, len(external_brca1_df)),
                    ("bridges_like_external_validation_brca2", external_brca2_config_path, len(external_brca2_df)),
                ]
                if size > 0
            ],
            workspace_root=root,
        ),
        encoding="utf-8",
    )

    artifact_paths = {
        "training_table": str(training_output_path.resolve()),
        "clinvar_expert_table": str(clinvar_expert_output_path.resolve()),
        "clinvar_expert_brca1_table": str(clinvar_expert_brca1_output_path.resolve()),
        "clinvar_expert_brca2_table": str(clinvar_expert_brca2_output_path.resolve()),
        "external_table": str(external_output_path.resolve()),
        "external_brca1_table": str(external_brca1_output_path.resolve()),
        "external_brca2_table": str(external_brca2_output_path.resolve()),
        "enigma_table": str(enigma_output_path.resolve()),
        "gnomad_table": str(gnomad_output_path.resolve()),
        "mavedb_table": str(mavedb_output_path.resolve()),
    }
    config_paths = {
        "training_config": str(real_config_path.resolve()),
        "clinvar_expert_config": str(clinvar_expert_config_path.resolve()),
        "clinvar_expert_brca1_config": str(clinvar_expert_brca1_config_path.resolve()),
        "clinvar_expert_brca2_config": str(clinvar_expert_brca2_config_path.resolve()),
        "external_config": str(external_config_path.resolve()),
        "external_brca1_config": str(external_brca1_config_path.resolve()),
        "external_brca2_config": str(external_brca2_config_path.resolve()),
        "benchmark_config": str(benchmark_config_path.resolve()),
    }
    validations = {
        "training": _validate_prepared_artifact(training_output_path, "clinvar_variant_summary"),
        "clinvar_expert": _validate_prepared_artifact(clinvar_expert_output_path, "clinvar_variant_summary"),
        "clinvar_expert_brca1": _validate_prepared_artifact(clinvar_expert_brca1_output_path, "clinvar_variant_summary"),
        "clinvar_expert_brca2": _validate_prepared_artifact(clinvar_expert_brca2_output_path, "clinvar_variant_summary"),
        "external": _validate_prepared_artifact(external_output_path, "clinvar_variant_summary"),
        "external_brca1": _validate_prepared_artifact(external_brca1_output_path, "clinvar_variant_summary"),
        "external_brca2": _validate_prepared_artifact(external_brca2_output_path, "clinvar_variant_summary"),
        "gnomad": _validate_prepared_artifact(gnomad_output_path, "gnomad_variant_table"),
        "mavedb": _validate_prepared_artifact(mavedb_output_path, "mavedb_score_table"),
    }
    bundle = {
        "summary": {
            "generated_at": _now_utc(),
            "workspace_root": str(root.resolve()),
            "training_rows": int(len(training_df)),
            "clinvar_expert_rows": int(len(clinvar_expert_df)),
            "clinvar_expert_brca1_rows": int(len(clinvar_expert_brca1_df)),
            "clinvar_expert_brca2_rows": int(len(clinvar_expert_brca2_df)),
            "external_rows": int(len(external_df)),
            "external_brca1_rows": int(len(external_brca1_df)),
            "external_brca2_rows": int(len(external_brca2_df)),
            "enigma_rows": int(len(enigma_df)),
            "gnomad_rows": int(len(gnomad_df)),
            "mavedb_rows": int(len(mavedb_df)),
            "benchmark_external_cohort_count": int(
                sum(
                    1
                    for size in [
                        len(clinvar_expert_brca1_df),
                        len(clinvar_expert_brca2_df),
                        len(external_brca1_df),
                        len(external_brca2_df),
                    ]
                    if size > 0
                )
            ),
        },
        "training_summary": training_summary,
        "brca_exchange_summary": brca_summary,
        "gnomad_summary": brca_summary.get("gnomad_summary") or {},
        "mavedb_summary": mavedb_summary,
        "artifact_paths": artifact_paths,
        "config_paths": config_paths,
        "input_fingerprints": _artifact_fingerprints(
            {
                "clinvar_input": str(clinvar_input),
                "brca_exchange_input": str(brca_input),
                "mavedb_input": str(mavedb_input),
                "gnomad_input": str(gnomad_input) if gnomad_input else None,
            }
        ),
        "artifact_fingerprints": _artifact_fingerprints({**artifact_paths, **config_paths}),
        "validations": validations,
    }
    bundle["markdown_report"] = _build_real_data_preparation_markdown(bundle)
    bundle["html_report"] = _render_markdown_html(bundle["markdown_report"], "PrimeVarClass Real-data Preparation")
    return bundle


def export_real_data_preparation_bundle(
    *,
    clinvar_variant_summary_path: str,
    brca_exchange_release_path: str,
    mavedb_dump_path: str,
    output_dir: str,
    workspace_root: str | None = None,
    gnomad_annotations_path: str | None = None,
) -> dict:
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    bundle = build_real_data_preparation_bundle(
        clinvar_variant_summary_path=clinvar_variant_summary_path,
        brca_exchange_release_path=brca_exchange_release_path,
        mavedb_dump_path=mavedb_dump_path,
        output_dir=str(output_root),
        workspace_root=workspace_root,
        gnomad_annotations_path=gnomad_annotations_path,
    )
    markdown_path = output_root / "real_data_preparation_report.md"
    html_path = output_root / "real_data_preparation_report.html"
    manifest_path = output_root / "real_data_preparation_manifest.json"
    markdown_path.write_text(str(bundle.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(str(bundle.get("html_report") or ""), encoding="utf-8")
    manifest_payload = {
        "generated_at": _now_utc(),
        "summary": bundle.get("summary"),
        "training_summary": _jsonify(bundle.get("training_summary") or {}),
        "brca_exchange_summary": _jsonify(bundle.get("brca_exchange_summary") or {}),
        "gnomad_summary": _jsonify(bundle.get("gnomad_summary") or {}),
        "mavedb_summary": _jsonify(bundle.get("mavedb_summary") or {}),
        "artifact_paths": bundle.get("artifact_paths"),
        "config_paths": bundle.get("config_paths"),
        "input_fingerprints": bundle.get("input_fingerprints"),
        "artifact_fingerprints": bundle.get("artifact_fingerprints"),
        "validations": bundle.get("validations"),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
    }
    manifest_path.write_text(json.dumps(_jsonify(manifest_payload), indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "real_data_preparation": bundle,
        "real_data_preparation_summary": bundle.get("summary") or {},
        "real_data_preparation_manifest_path": str(manifest_path),
        "real_data_preparation_report_markdown_path": str(markdown_path),
        "real_data_preparation_report_html_path": str(html_path),
        "artifact_paths": bundle.get("artifact_paths") or {},
        "config_paths": bundle.get("config_paths") or {},
    }
