from __future__ import annotations

import argparse
import csv
import gzip
import io
import urllib.request
from pathlib import Path
from typing import Iterable, TextIO

import pandas as pd


def _canonical_chrom(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.lower().startswith("chr"):
        return "chr" + text[3:]
    return "chr" + text


def _canonical_pos(value: object) -> str:
    try:
        return str(int(float(str(value).strip())))
    except Exception:
        return str(value or "").strip()


def _key(chrom: object, pos: object, ref: object, alt: object) -> str:
    parts = [_canonical_chrom(chrom), _canonical_pos(pos), str(ref or "").strip(), str(alt or "").strip()]
    return ":".join(parts) if all(parts) else ""


def _open_text(path_or_url: str) -> TextIO:
    if path_or_url.startswith(("http://", "https://")):
        response = urllib.request.urlopen(path_or_url, timeout=60)
        if path_or_url.endswith((".gz", ".bgz")):
            return io.TextIOWrapper(gzip.GzipFile(fileobj=response), encoding="utf-8", errors="replace")
        return io.TextIOWrapper(response, encoding="utf-8", errors="replace")

    path = Path(path_or_url).expanduser()
    if path.suffix.lower() in {".gz", ".bgz"}:
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("r", encoding="utf-8", errors="replace")


def _load_targets(path: Path) -> dict[str, dict[str, str]]:
    targets = pd.read_csv(path)
    target_map: dict[str, dict[str, str]] = {}
    for _, row in targets.iterrows():
        chrom = row.get("chromosome") or row.get("chrom") or row.get("#CHROM")
        pos = row.get("position_vcf") or row.get("POS") or row.get("Start")
        ref = row.get("reference_allele_vcf") or row.get("ReferenceAllele") or row.get("REF")
        alt = row.get("alternate_allele_vcf") or row.get("AlternateAllele") or row.get("ALT")
        key = _key(chrom, pos, ref, alt)
        if not key:
            continue
        target_map[key] = {
            "gene": str(row.get("gene") or "").strip(),
            "hgvs_p": str(row.get("hgvs_p") or "").strip(),
            "variation_id": str(row.get("variation_id") or "").strip(),
            "target_key": key,
        }
    return target_map


def _iter_alphamissense_rows(handle: Iterable[str]) -> Iterable[dict[str, str]]:
    header: list[str] | None = None
    for line in handle:
        if not line.strip():
            continue
        if line.startswith("##"):
            continue
        if header is None:
            header = line.rstrip("\n").split("\t")
            if header and header[0] == "#CHROM":
                header[0] = "CHROM"
            continue
        if header is None:
            continue
        values = line.rstrip("\n").split("\t")
        yield dict(zip(header, values))


def extract_subset(
    *,
    alphamissense_input: str,
    targets_path: Path,
    output_path: Path,
    max_lines: int | None = None,
    max_matches: int | None = None,
) -> dict[str, int]:
    targets = _load_targets(targets_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    scanned = 0
    matched = 0
    fieldnames = [
        "gene",
        "hgvs_p",
        "feature_alphamissense_pathogenicity",
        "feature_alphamissense_class",
        "meta_alphamissense_transcript_id",
        "meta_genome_build",
        "meta_uniprot_accession",
        "meta_chrom",
        "meta_pos",
        "meta_ref",
        "meta_alt",
        "meta_alphamissense_protein_variant",
        "meta_clinvar_variation_id",
        "target_key",
    ]
    with _open_text(alphamissense_input) as handle, output_path.open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in _iter_alphamissense_rows(handle):
            scanned += 1
            key = _key(row.get("CHROM") or row.get("#CHROM"), row.get("POS"), row.get("REF"), row.get("ALT"))
            target = targets.get(key)
            if target:
                writer.writerow(
                    {
                        "gene": target["gene"],
                        "hgvs_p": target["hgvs_p"],
                        "feature_alphamissense_pathogenicity": row.get("am_pathogenicity", ""),
                        "feature_alphamissense_class": row.get("am_class", ""),
                        "meta_alphamissense_transcript_id": row.get("transcript_id", ""),
                        "meta_genome_build": row.get("genome", ""),
                        "meta_uniprot_accession": row.get("uniprot_id", ""),
                        "meta_chrom": row.get("CHROM") or row.get("#CHROM", ""),
                        "meta_pos": row.get("POS", ""),
                        "meta_ref": row.get("REF", ""),
                        "meta_alt": row.get("ALT", ""),
                        "meta_alphamissense_protein_variant": row.get("protein_variant", ""),
                        "meta_clinvar_variation_id": target["variation_id"],
                        "target_key": key,
                    }
                )
                matched += 1
                if max_matches is not None and matched >= max_matches:
                    break
            if max_lines is not None and scanned >= max_lines:
                break
    return {"target_count": len(targets), "rows_scanned": scanned, "rows_matched": matched}


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract a target-variant AlphaMissense subset by genomic coordinate.")
    parser.add_argument("--alphamissense-input", required=True, help="Local file or URL, for example AlphaMissense_hg38.tsv.gz.")
    parser.add_argument("--targets", required=True, help="CSV with frozen variants and GRCh38 coordinates.")
    parser.add_argument("--output", default="data/raw/alphamissense/target_gene_alphamissense.tsv")
    parser.add_argument("--max-lines", type=int, default=None, help="Optional safety cap for smoke tests.")
    parser.add_argument("--max-matches", type=int, default=None, help="Optional stop after N matched rows.")
    args = parser.parse_args()
    summary = extract_subset(
        alphamissense_input=args.alphamissense_input,
        targets_path=Path(args.targets),
        output_path=Path(args.output),
        max_lines=args.max_lines,
        max_matches=args.max_matches,
    )
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
