
from __future__ import annotations

import math
import os
import re
import warnings
from dataclasses import asdict, dataclass
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    matthews_corrcoef,
    roc_auc_score,
    confusion_matrix,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# Optional gradient boosting imports (graceful degradation)
try:
    from xgboost import XGBClassifier
    _HAS_XGBOOST = True
except ImportError:
    _HAS_XGBOOST = False

try:
    from lightgbm import LGBMClassifier
    _HAS_LIGHTGBM = True
except ImportError:
    _HAS_LIGHTGBM = False


# ============================================================
# PRIMEVARCLASS - CONSOLIDATED STARTER SCRIPT
# ============================================================

AMINO_ACID_DATA = [
    {"aa1": "A", "aa3": "Ala", "name": "Alanine", "mass": 89.09, "hydro": 1.8, "charge": 0, "polar": 0, "aromatic": 0, "prime_mass_residue": 1, "class_group": "small_nonpolar", "codon_count": 4},
    {"aa1": "R", "aa3": "Arg", "name": "Arginine", "mass": 174.20, "hydro": -4.5, "charge": 1, "polar": 1, "aromatic": 0, "prime_mass_residue": 0, "class_group": "basic", "codon_count": 6},
    {"aa1": "N", "aa3": "Asn", "name": "Asparagine", "mass": 132.12, "hydro": -3.5, "charge": 0, "polar": 1, "aromatic": 0, "prime_mass_residue": 0, "class_group": "polar", "codon_count": 2},
    {"aa1": "D", "aa3": "Asp", "name": "Aspartic Acid", "mass": 133.10, "hydro": -3.5, "charge": -1, "polar": 1, "aromatic": 0, "prime_mass_residue": 0, "class_group": "acidic", "codon_count": 2},
    {"aa1": "C", "aa3": "Cys", "name": "Cysteine", "mass": 121.16, "hydro": 2.5, "charge": 0, "polar": 1, "aromatic": 0, "prime_mass_residue": 0, "class_group": "special", "codon_count": 2},
    {"aa1": "Q", "aa3": "Gln", "name": "Glutamine", "mass": 146.15, "hydro": -3.5, "charge": 0, "polar": 1, "aromatic": 0, "prime_mass_residue": 0, "class_group": "polar", "codon_count": 2},
    {"aa1": "E", "aa3": "Glu", "name": "Glutamic Acid", "mass": 147.13, "hydro": -3.5, "charge": -1, "polar": 1, "aromatic": 0, "prime_mass_residue": 0, "class_group": "acidic", "codon_count": 2},
    {"aa1": "G", "aa3": "Gly", "name": "Glycine", "mass": 75.07, "hydro": -0.4, "charge": 0, "polar": 0, "aromatic": 0, "prime_mass_residue": 1, "class_group": "small_nonpolar", "codon_count": 4},
    {"aa1": "H", "aa3": "His", "name": "Histidine", "mass": 155.16, "hydro": -3.2, "charge": 1, "polar": 1, "aromatic": 1, "prime_mass_residue": 0, "class_group": "basic", "codon_count": 2},
    {"aa1": "I", "aa3": "Ile", "name": "Isoleucine", "mass": 131.18, "hydro": 4.5, "charge": 0, "polar": 0, "aromatic": 0, "prime_mass_residue": 1, "class_group": "hydrophobic", "codon_count": 3},
    {"aa1": "L", "aa3": "Leu", "name": "Leucine", "mass": 131.18, "hydro": 3.8, "charge": 0, "polar": 0, "aromatic": 0, "prime_mass_residue": 1, "class_group": "hydrophobic", "codon_count": 6},
    {"aa1": "K", "aa3": "Lys", "name": "Lysine", "mass": 146.19, "hydro": -3.9, "charge": 1, "polar": 1, "aromatic": 0, "prime_mass_residue": 0, "class_group": "basic", "codon_count": 2},
    {"aa1": "M", "aa3": "Met", "name": "Methionine", "mass": 149.21, "hydro": 1.9, "charge": 0, "polar": 0, "aromatic": 0, "prime_mass_residue": 0, "class_group": "hydrophobic", "codon_count": 1},
    {"aa1": "F", "aa3": "Phe", "name": "Phenylalanine", "mass": 165.19, "hydro": 2.8, "charge": 0, "polar": 0, "aromatic": 1, "prime_mass_residue": 1, "class_group": "aromatic", "codon_count": 2},
    {"aa1": "P", "aa3": "Pro", "name": "Proline", "mass": 115.13, "hydro": -1.6, "charge": 0, "polar": 0, "aromatic": 0, "prime_mass_residue": 1, "class_group": "special", "codon_count": 4},
    {"aa1": "S", "aa3": "Ser", "name": "Serine", "mass": 105.09, "hydro": -0.8, "charge": 0, "polar": 1, "aromatic": 0, "prime_mass_residue": 0, "class_group": "polar", "codon_count": 6},
    {"aa1": "T", "aa3": "Thr", "name": "Threonine", "mass": 119.12, "hydro": -0.7, "charge": 0, "polar": 1, "aromatic": 0, "prime_mass_residue": 1, "class_group": "polar", "codon_count": 4},
    {"aa1": "W", "aa3": "Trp", "name": "Tryptophan", "mass": 204.23, "hydro": -0.9, "charge": 0, "polar": 0, "aromatic": 1, "prime_mass_residue": 0, "class_group": "aromatic", "codon_count": 1},
    {"aa1": "Y", "aa3": "Tyr", "name": "Tyrosine", "mass": 181.19, "hydro": -1.3, "charge": 0, "polar": 1, "aromatic": 1, "prime_mass_residue": 1, "class_group": "aromatic", "codon_count": 2},
    {"aa1": "V", "aa3": "Val", "name": "Valine", "mass": 117.15, "hydro": 4.2, "charge": 0, "polar": 0, "aromatic": 0, "prime_mass_residue": 1, "class_group": "hydrophobic", "codon_count": 4},
]

AA_TABLE = pd.DataFrame(AMINO_ACID_DATA)
AA1_MAP: Dict[str, dict] = {row["aa1"]: row for row in AMINO_ACID_DATA}
AA3_TO_AA1: Dict[str, str] = {row["aa3"].lower(): row["aa1"] for row in AMINO_ACID_DATA}
GENE_SYMBOL_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9-]*$")
GENE_PREFIXED_HGVS_PATTERN = re.compile(r"^([A-Za-z][A-Za-z0-9-]*)\s+(p\..+)$", flags=re.IGNORECASE)
MISSENSE_VARIANT_PATTERN = re.compile(
    r"^([A-Za-z][A-Za-z0-9-]*)\s+p\.([A-Za-z]{1,3})(\d+)([A-Za-z]{1,3})$",
    flags=re.IGNORECASE,
)


def _parallel_jobs_default() -> int:
    raw_value = str(os.getenv("PRIMEVARCLASS_N_JOBS", "1") or "1").strip()
    try:
        parsed = int(raw_value)
    except ValueError:
        return 1
    return parsed if parsed != 0 else 1


DEFAULT_PARALLEL_JOBS = _parallel_jobs_default()

PRIME_BY_CODON_COUNT = {1: 2, 2: 3, 3: 5, 4: 7, 6: 11}
CLASS_GROUP_ORDER = {"small_nonpolar": 1, "special": 2, "polar": 3, "acidic": 4, "basic": 5, "hydrophobic": 6, "aromatic": 7}
HYDRO_CLASS = {
    "strong_hydrophilic": (-10.0, -2.0),
    "mild_hydrophilic": (-2.0, 0.0),
    "mild_hydrophobic": (0.0, 2.5),
    "strong_hydrophobic": (2.5, 10.0),
}
SEVERITY_WEIGHTS = {"charge_diff": 1.5, "hydro_diff": 1.0, "mass_diff": 0.03, "polar_switch": 1.2, "aromatic_switch": 1.2, "class_change": 1.0}

REQUIRED_DATASET_COLUMNS = ["gene", "hgvs_p", "label"]
OPTIONAL_DATASET_COLUMNS = [
    "review_status", "source", "clinical_significance", "variant_id",
    "phylop", "gerp", "siphy",
    "rsa", "ddg_foldx", "functional_domain", "protein_interface", "distance_to_key_site",
    "revel", "bayesdel", "alphamissense", "cadd",
]
PASSTHROUGH_FEATURE_PREFIXES = ("feature_",)
PASSTHROUGH_METADATA_PREFIXES = ("meta_",)
NON_FEATURE_METADATA_COLUMNS = {
    "label", "variant", "review_status", "source", "clinical_significance", "variant_id",
    "source_name", "source_kind", "source_type", "hgvs_p", "protein_change_raw", "name",
    "meta_dataset", "meta_source_url", "meta_mavedb_urn", "meta_assay_name",
}

LABEL_MAP = {
    "pathogenic": 1, "likely pathogenic": 1, "pathogenic/likely pathogenic": 1,
    "benign": 0, "likely benign": 0, "benign/likely benign": 0,
    "probably pathogenic": 1, "probably benign": 0,
    "p": 1, "lp": 1, "b": 0, "lb": 0, 1: 1, 0: 0, "1": 1, "0": 0,
}
EXCLUDED_LABELS = {"vus", "uncertain significance", "variant of uncertain significance", "conflicting", "conflicting classifications", "not provided"}

ACMG_PATHOGENIC_LR_THRESHOLDS = {"supporting": 2.08, "moderate": 4.33, "strong": 18.7}
ACMG_BENIGN_LR_THRESHOLDS = {"supporting": 0.48, "moderate": 0.23, "strong": 0.05}
DEFAULT_MODEL_FAMILY = "random_forest"
SUPPORTED_MODEL_FAMILIES = {"random_forest", "extra_trees", "logistic_regression", "xgboost", "lightgbm"}
MODEL_FAMILY_ALIASES = {
    "rf": "random_forest",
    "randomforest": "random_forest",
    "random_forest": "random_forest",
    "extra_trees": "extra_trees",
    "extratrees": "extra_trees",
    "et": "extra_trees",
    "logistic": "logistic_regression",
    "logreg": "logistic_regression",
    "logistic_regression": "logistic_regression",
    "xgboost": "xgboost",
    "xgb": "xgboost",
    "gradient_boosting": "xgboost",
    "lightgbm": "lightgbm",
    "lgbm": "lightgbm",
    "lgb": "lightgbm",
}


@dataclass
class MissenseVariant:
    gene: str
    aa_ref: str
    position: int
    aa_alt: str

    @property
    def variant_str(self) -> str:
        return f"{self.gene} p.{self.aa_ref}{self.position}{self.aa_alt}"


@dataclass
class PrimeEncodingResult:
    mode: str
    prime_ref: int
    prime_alt: int


@dataclass
class DatasetBuildReport:
    input_rows: int
    valid_rows: int
    excluded_missing: int
    excluded_invalid_gene: int
    excluded_invalid_label: int
    excluded_non_missense: int
    excluded_class_imbalance_risk: int = 0


def normalize_amino_acid_code(code: str) -> str:
    code = str(code).strip()
    if len(code) == 1:
        aa = code.upper()
        if aa not in AA1_MAP:
            raise ValueError(f"Aminoácido inválido: {code}")
        return aa
    aa = AA3_TO_AA1.get(code.lower())
    if aa is None:
        raise ValueError(f"Código de aminoácido inválido: {code}")
    return aa


def parse_variant(text: str) -> MissenseVariant:
    match = MISSENSE_VARIANT_PATTERN.match(str(text).strip())
    if not match:
        raise ValueError(f"Formato inválido de variante: {text}")
    gene, ref_raw, pos_raw, alt_raw = match.groups()
    normalized_gene = normalize_gene(gene)
    if normalized_gene is None:
        raise ValueError(f"Gene invÃ¡lido: {gene}")
    aa_ref = normalize_amino_acid_code(ref_raw)
    aa_alt = normalize_amino_acid_code(alt_raw)
    if aa_ref == aa_alt:
        raise ValueError("A variante não é missense.")
    return MissenseVariant(gene=normalized_gene, aa_ref=aa_ref, position=int(pos_raw), aa_alt=aa_alt)


def get_aa_props(aa1: str) -> dict:
    return AA1_MAP[aa1]


def classify_hydrophobicity(value: float) -> str:
    for class_name, (lower, upper) in HYDRO_CLASS.items():
        if lower <= value < upper:
            return class_name
    return "unknown"


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    limit = int(math.sqrt(n)) + 1
    for i in range(3, limit, 2):
        if n % i == 0:
            return False
    return True


def next_prime(n: int) -> int:
    candidate = max(2, int(n))
    while not is_prime(candidate):
        candidate += 1
    return candidate


def previous_prime(n: int) -> int:
    candidate = int(n) - 1
    while candidate >= 2:
        if is_prime(candidate):
            return candidate
        candidate -= 1
    return 2


def following_prime(n: int) -> int:
    candidate = int(n) + 1
    while not is_prime(candidate):
        candidate += 1
    return candidate


def is_twin_prime_member(n: int) -> bool:
    value = int(n)
    return is_prime(value) and (is_prime(value - 2) or is_prime(value + 2))


def is_sophie_germain_prime(n: int) -> bool:
    value = int(n)
    return is_prime(value) and is_prime((2 * value) + 1)


def _prime_gap_context(n: int) -> dict:
    value = max(2, int(n))
    prev_value = previous_prime(value)
    next_value = following_prime(value)
    gap_before = value - prev_value if value > 2 else 0
    gap_after = next_value - value
    span = gap_before + gap_after
    density = (2.0 / span) if span > 0 else 0.0
    asymmetry = ((gap_after - gap_before) / span) if span > 0 else 0.0
    return {
        "previous_prime": prev_value,
        "following_prime": next_value,
        "gap_before": gap_before,
        "gap_after": gap_after,
        "gap_span": span,
        "local_density": round(density, 6),
        "neighbor_asymmetry": round(asymmetry, 6),
        "is_twin_prime_member": int(is_twin_prime_member(value)),
        "is_sophie_germain_prime": int(is_sophie_germain_prime(value)),
        "mod_6": value % 6,
        "mod_30": value % 30,
    }


def get_prime_value(aa1: str, mode: str = "hybrid") -> int:
    props = get_aa_props(aa1)
    mode = mode.lower()

    if mode == "codon":
        return PRIME_BY_CODON_COUNT[props["codon_count"]]

    if mode == "prime_mass":
        base_map = {"small_nonpolar": 2, "special": 3, "polar": 5, "acidic": 7, "basic": 11, "hydrophobic": 13, "aromatic": 17}
        base_prime = base_map[props["class_group"]]
        return base_prime * 2 + 1 if props["prime_mass_residue"] else base_prime

    if mode == "hybrid":
        codon_prime = PRIME_BY_CODON_COUNT[props["codon_count"]]
        class_rank = CLASS_GROUP_ORDER[props["class_group"]]
        aromatic_bonus = 2 if props["aromatic"] else 0
        charge_bonus = 3 if props["charge"] != 0 else 0
        prime_mass_bonus = 5 if props["prime_mass_residue"] else 0
        return next_prime(codon_prime + class_rank + aromatic_bonus + charge_bonus + prime_mass_bonus)

    raise ValueError("Modo inválido. Use: codon, prime_mass ou hybrid.")


def encode_variant_primes(variant: MissenseVariant, mode: str = "hybrid") -> PrimeEncodingResult:
    return PrimeEncodingResult(mode=mode, prime_ref=get_prime_value(variant.aa_ref, mode), prime_alt=get_prime_value(variant.aa_alt, mode))


def compute_biochemical_severity(ref: dict, alt: dict) -> float:
    charge_diff = abs(alt["charge"] - ref["charge"])
    hydro_diff = abs(alt["hydro"] - ref["hydro"])
    mass_diff = abs(alt["mass"] - ref["mass"])
    polar_switch = int(ref["polar"] != alt["polar"])
    aromatic_switch = int(ref["aromatic"] != alt["aromatic"])
    class_change = int(ref["class_group"] != alt["class_group"])
    score = (
        charge_diff * SEVERITY_WEIGHTS["charge_diff"]
        + hydro_diff * SEVERITY_WEIGHTS["hydro_diff"]
        + mass_diff * SEVERITY_WEIGHTS["mass_diff"]
        + polar_switch * SEVERITY_WEIGHTS["polar_switch"]
        + aromatic_switch * SEVERITY_WEIGHTS["aromatic_switch"]
        + class_change * SEVERITY_WEIGHTS["class_change"]
    )
    return round(score, 4)


def encode_variant_features(variant: MissenseVariant, mode: str = "hybrid", external_features: dict | None = None) -> dict:
    ref = get_aa_props(variant.aa_ref)
    alt = get_aa_props(variant.aa_alt)
    encoded = encode_variant_primes(variant, mode=mode)
    ref_prime_context = _prime_gap_context(encoded.prime_ref)
    alt_prime_context = _prime_gap_context(encoded.prime_alt)

    hydro_class_ref = classify_hydrophobicity(ref["hydro"])
    hydro_class_alt = classify_hydrophobicity(alt["hydro"])
    prime_diff = abs(encoded.prime_alt - encoded.prime_ref)
    mean_gap_span = max((ref_prime_context["gap_span"] + alt_prime_context["gap_span"]) / 2.0, 1.0)
    twin_transition = f"{ref_prime_context['is_twin_prime_member']}->{alt_prime_context['is_twin_prime_member']}"
    sophie_transition = f"{ref_prime_context['is_sophie_germain_prime']}->{alt_prime_context['is_sophie_germain_prime']}"
    mod_30_transition = f"{ref_prime_context['mod_30']}->{alt_prime_context['mod_30']}"

    features = {
        "prime_mode": mode,
        "gene": variant.gene,
        "aa_ref": variant.aa_ref,
        "aa_alt": variant.aa_alt,
        "position": variant.position,
        "prime_ref": encoded.prime_ref,
        "prime_alt": encoded.prime_alt,
        "prime_diff": prime_diff,
        "prime_ratio": encoded.prime_alt / encoded.prime_ref,
        "prime_log_ratio": math.log(encoded.prime_alt / encoded.prime_ref),
        "prime_product": encoded.prime_ref * encoded.prime_alt,
        "prime_is_increase": int(encoded.prime_alt > encoded.prime_ref),
        "prime_is_decrease": int(encoded.prime_alt < encoded.prime_ref),
        "prime_distance_rank": abs(encoded.prime_alt - encoded.prime_ref),
        "prime_previous_ref": ref_prime_context["previous_prime"],
        "prime_previous_alt": alt_prime_context["previous_prime"],
        "prime_following_ref": ref_prime_context["following_prime"],
        "prime_following_alt": alt_prime_context["following_prime"],
        "prime_gap_before_ref": ref_prime_context["gap_before"],
        "prime_gap_before_alt": alt_prime_context["gap_before"],
        "prime_gap_after_ref": ref_prime_context["gap_after"],
        "prime_gap_after_alt": alt_prime_context["gap_after"],
        "prime_gap_span_ref": ref_prime_context["gap_span"],
        "prime_gap_span_alt": alt_prime_context["gap_span"],
        "prime_gap_delta": alt_prime_context["gap_span"] - ref_prime_context["gap_span"],
        "prime_local_density_ref": ref_prime_context["local_density"],
        "prime_local_density_alt": alt_prime_context["local_density"],
        "prime_local_density_delta": round(alt_prime_context["local_density"] - ref_prime_context["local_density"], 6),
        "prime_neighbor_asymmetry_ref": ref_prime_context["neighbor_asymmetry"],
        "prime_neighbor_asymmetry_alt": alt_prime_context["neighbor_asymmetry"],
        "prime_neighbor_asymmetry_delta": round(alt_prime_context["neighbor_asymmetry"] - ref_prime_context["neighbor_asymmetry"], 6),
        "prime_curvature_score": round(prime_diff / mean_gap_span, 6),
        "prime_mod_6_ref": ref_prime_context["mod_6"],
        "prime_mod_6_alt": alt_prime_context["mod_6"],
        "prime_mod_6_delta": alt_prime_context["mod_6"] - ref_prime_context["mod_6"],
        "prime_mod_30_ref": ref_prime_context["mod_30"],
        "prime_mod_30_alt": alt_prime_context["mod_30"],
        "prime_mod_30_delta": alt_prime_context["mod_30"] - ref_prime_context["mod_30"],
        "prime_mod_30_transition": mod_30_transition,
        "prime_twin_ref": ref_prime_context["is_twin_prime_member"],
        "prime_twin_alt": alt_prime_context["is_twin_prime_member"],
        "prime_twin_transition": twin_transition,
        "prime_sophie_germain_ref": ref_prime_context["is_sophie_germain_prime"],
        "prime_sophie_germain_alt": alt_prime_context["is_sophie_germain_prime"],
        "prime_sophie_transition": sophie_transition,
        "mass_ref": ref["mass"],
        "mass_alt": alt["mass"],
        "mass_diff": alt["mass"] - ref["mass"],
        "mass_abs_diff": abs(alt["mass"] - ref["mass"]),
        "hydro_ref": ref["hydro"],
        "hydro_alt": alt["hydro"],
        "hydro_diff": alt["hydro"] - ref["hydro"],
        "hydro_abs_diff": abs(alt["hydro"] - ref["hydro"]),
        "charge_ref": ref["charge"],
        "charge_alt": alt["charge"],
        "charge_diff": alt["charge"] - ref["charge"],
        "charge_abs_diff": abs(alt["charge"] - ref["charge"]),
        "polar_switch": int(ref["polar"] != alt["polar"]),
        "aromatic_switch": int(ref["aromatic"] != alt["aromatic"]),
        "prime_mass_retention": int(ref["prime_mass_residue"] == alt["prime_mass_residue"]),
        "mass_prime_transition": f"{ref['prime_mass_residue']}->{alt['prime_mass_residue']}",
        "hydro_class_ref": hydro_class_ref,
        "hydro_class_alt": hydro_class_alt,
        "hydro_class_transition": f"{hydro_class_ref}->{hydro_class_alt}",
        "class_group_ref": ref["class_group"],
        "class_group_alt": alt["class_group"],
        "conservative_class_change": int(ref["class_group"] == alt["class_group"]),
        "charge_transition_type": f"{ref['charge']}->{alt['charge']}",
        "codon_count_ref": ref["codon_count"],
        "codon_count_alt": alt["codon_count"],
        "codon_count_diff": alt["codon_count"] - ref["codon_count"],
        "biochemical_severity_score": compute_biochemical_severity(ref, alt),
        "phylop": np.nan,
        "gerp": np.nan,
        "siphy": np.nan,
        "rsa": np.nan,
        "ddg_foldx": np.nan,
        "functional_domain": "unknown",
        "protein_interface": "unknown",
        "distance_to_key_site": np.nan,
        "revel": np.nan,
        "bayesdel": np.nan,
        "alphamissense": np.nan,
        "cadd": np.nan,
    }

    if external_features:
        for key, value in external_features.items():
            if key in features:
                features[key] = value

    features["has_conservation_data"] = int(pd.notna(features["phylop"]) or pd.notna(features["gerp"]) or pd.notna(features["siphy"]))
    features["has_structure_data"] = int(pd.notna(features["rsa"]) or pd.notna(features["ddg_foldx"]) or pd.notna(features["distance_to_key_site"]))
    features["in_functional_domain"] = int(features["functional_domain"] != "unknown")
    features["in_protein_interface"] = int(str(features["protein_interface"]).lower() in {"1", "true", "yes", "interface"})
    conservation_values = [float(x) for x in [features["phylop"], features["gerp"], features["siphy"]] if pd.notna(x)]
    structure_values = [float(x) for x in [features["rsa"], features["ddg_foldx"], features["distance_to_key_site"]] if pd.notna(x)]
    features["conservation_signal_mean"] = float(np.mean(conservation_values)) if conservation_values else np.nan
    features["structure_signal_mean"] = float(np.mean(structure_values)) if structure_values else np.nan
    return features


def normalize_label(value) -> int | None:
    if pd.isna(value):
        return None
    if isinstance(value, str):
        key = value.strip().lower()
        if key in EXCLUDED_LABELS:
            return None
        return LABEL_MAP.get(key)
    return LABEL_MAP.get(value)


def normalize_gene(value: str) -> str | None:
    if pd.isna(value):
        return None
    gene = str(value).strip().upper()
    if not gene or not GENE_SYMBOL_PATTERN.fullmatch(gene):
        return None
    return gene


def normalize_hgvs_protein(value: str, gene: str | None = None) -> str | None:
    if pd.isna(value):
        return None
    raw = str(value).strip()
    if not raw:
        return None
    normalized_gene = normalize_gene(gene) if gene is not None and not pd.isna(gene) else None
    prefixed_match = GENE_PREFIXED_HGVS_PATTERN.match(raw)
    if prefixed_match:
        prefixed_gene = normalize_gene(prefixed_match.group(1))
        protein_change = prefixed_match.group(2)
        if prefixed_gene is None:
            return None
        return f"{prefixed_gene} p.{protein_change[2:]}"
    if any(character.isspace() for character in raw):
        return None
    if raw.lower().startswith("p."):
        return f"{normalized_gene} p.{raw[2:]}" if normalized_gene else None
    return f"{normalized_gene} p.{raw}" if normalized_gene else None


def _normalize_gene_allowlist(gene_allowlist: List[str] | None) -> set[str] | None:
    if not gene_allowlist:
        return None
    normalized = {gene for gene in (normalize_gene(value) for value in gene_allowlist) if gene}
    return normalized or None


def _iter_available_genes(df: pd.DataFrame) -> List[str]:
    if "gene" not in df.columns:
        return []
    genes: List[str] = []
    seen: set[str] = set()
    for value in df["gene"].tolist():
        gene = normalize_gene(value)
        if gene and gene not in seen:
            seen.add(gene)
            genes.append(gene)
    return genes


def is_supported_missense(hgvs_p: str) -> bool:
    try:
        parse_variant(hgvs_p)
        return True
    except Exception:
        return False


def validate_dataset_columns(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_DATASET_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes: {missing}")


def get_passthrough_feature_columns(df: pd.DataFrame) -> List[str]:
    return [col for col in df.columns if any(col.startswith(prefix) for prefix in PASSTHROUGH_FEATURE_PREFIXES)]


def get_passthrough_metadata_columns(df: pd.DataFrame) -> List[str]:
    return [col for col in df.columns if any(col.startswith(prefix) for prefix in PASSTHROUGH_METADATA_PREFIXES)]


def build_dataset_from_dataframe(
    df: pd.DataFrame,
    mode: str = "hybrid",
    keep_metadata: bool = True,
    gene_allowlist: List[str] | None = None,
) -> Tuple[pd.DataFrame, DatasetBuildReport]:
    validate_dataset_columns(df)
    rows = []
    excluded_missing = excluded_invalid_gene = excluded_invalid_label = excluded_non_missense = 0
    passthrough_feature_columns = get_passthrough_feature_columns(df)
    passthrough_metadata_columns = get_passthrough_metadata_columns(df)
    allowed_genes = _normalize_gene_allowlist(gene_allowlist)

    for _, row in df.iterrows():
        raw_gene = row.get("gene")
        raw_hgvs_p = row.get("hgvs_p")
        raw_label = row.get("label")

        if pd.isna(raw_gene) or pd.isna(raw_hgvs_p) or pd.isna(raw_label):
            excluded_missing += 1
            continue
        gene = normalize_gene(raw_gene)
        if gene is None or (allowed_genes is not None and gene not in allowed_genes):
            excluded_invalid_gene += 1
            continue
        hgvs_p = normalize_hgvs_protein(raw_hgvs_p, gene=gene)
        if hgvs_p is None:
            excluded_missing += 1
            continue
        label = normalize_label(raw_label)
        if label is None:
            excluded_invalid_label += 1
            continue
        if not is_supported_missense(hgvs_p):
            excluded_non_missense += 1
            continue

        variant = parse_variant(hgvs_p)
        if variant.gene != gene:
            excluded_invalid_gene += 1
            continue
        extra = {col: row.get(col) for col in OPTIONAL_DATASET_COLUMNS if col in df.columns}
        feat = encode_variant_features(variant, mode=mode, external_features=extra)
        for col in passthrough_feature_columns:
            feat[col] = row.get(col)
        feat["variant"] = variant.variant_str
        feat["label"] = label

        if keep_metadata:
            for col in OPTIONAL_DATASET_COLUMNS:
                if col in df.columns:
                    feat[col] = row.get(col)
            for col in passthrough_metadata_columns:
                feat[col] = row.get(col)

        rows.append(feat)

    built = pd.DataFrame(rows)
    report = DatasetBuildReport(
        input_rows=len(df),
        valid_rows=len(built),
        excluded_missing=excluded_missing,
        excluded_invalid_gene=excluded_invalid_gene,
        excluded_invalid_label=excluded_invalid_label,
        excluded_non_missense=excluded_non_missense,
    )
    return built, report


def build_dataset_from_csv(input_csv_path: str, output_csv_path: str | None = None, mode: str = "hybrid", keep_metadata: bool = True) -> Tuple[pd.DataFrame, DatasetBuildReport]:
    df = pd.read_csv(input_csv_path)
    built, report = build_dataset_from_dataframe(df, mode=mode, keep_metadata=keep_metadata)
    if output_csv_path:
        built.to_csv(output_csv_path, index=False)
    return built, report


def dataset_schema_template() -> pd.DataFrame:
    return pd.DataFrame([
        {"gene": "BRCA1", "hgvs_p": "p.Cys61Gly", "label": "Pathogenic", "review_status": "expert_panel", "source": "ClinVar", "clinical_significance": "Pathogenic", "variant_id": "example_001", "phylop": 7.2, "gerp": 5.8, "siphy": 12.4, "rsa": 0.08, "ddg_foldx": 2.1, "functional_domain": "RING", "protein_interface": "interface", "distance_to_key_site": 3.4, "revel": 0.94, "bayesdel": 0.67, "alphamissense": 0.98, "cadd": 27.5},
        {"gene": "BRCA1", "hgvs_p": "p.Ile21Val", "label": "Benign", "review_status": "multiple_submitters", "source": "ClinVar", "clinical_significance": "Benign", "variant_id": "example_002", "phylop": 0.4, "gerp": 0.2, "siphy": 0.7, "rsa": 0.51, "ddg_foldx": 0.1, "functional_domain": "unknown", "protein_interface": "no", "distance_to_key_site": 22.0, "revel": 0.03, "bayesdel": -0.41, "alphamissense": 0.07, "cadd": 1.2},
        {"gene": "BRCA2", "hgvs_p": "p.Gly2508Ser", "label": "Likely pathogenic", "review_status": "multiple_submitters", "source": "ClinVar", "clinical_significance": "Likely pathogenic", "variant_id": "example_003", "phylop": 5.9, "gerp": 4.7, "siphy": 8.2, "rsa": 0.14, "ddg_foldx": 1.6, "functional_domain": "DBD", "protein_interface": "interface", "distance_to_key_site": 5.8, "revel": 0.88, "bayesdel": 0.54, "alphamissense": 0.93, "cadd": 24.1},
        {"gene": "BRCA2", "hgvs_p": "p.Val2109Ile", "label": "Likely benign", "review_status": "multiple_submitters", "source": "ClinVar", "clinical_significance": "Likely benign", "variant_id": "example_004", "phylop": 0.8, "gerp": 0.6, "siphy": 1.1, "rsa": 0.44, "ddg_foldx": 0.2, "functional_domain": "unknown", "protein_interface": "no", "distance_to_key_site": 18.5, "revel": 0.11, "bayesdel": -0.22, "alphamissense": 0.16, "cadd": 3.5},
    ])


def export_dataset_template(output_csv_path: str = "primevarclass_dataset_template.csv") -> str:
    dataset_schema_template().to_csv(output_csv_path, index=False)
    return output_csv_path


def normalize_clinvar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    renamed = df.copy()
    aliases = {
        "GeneSymbol": "gene", "Gene": "gene", "gene_symbol": "gene",
        "Protein change": "hgvs_p", "HGVS_p": "hgvs_p", "protein_change": "hgvs_p",
        "ClinicalSignificance": "label", "clinical_significance": "label",
        "ReviewStatus": "review_status", "variation_id": "variant_id", "VariationID": "variant_id",
    }
    for old_col, new_col in aliases.items():
        if old_col in renamed.columns and new_col not in renamed.columns:
            renamed = renamed.rename(columns={old_col: new_col})
    if "source" not in renamed.columns:
        renamed["source"] = "ClinVar"
    return renamed


def filter_high_confidence_variants(df: pd.DataFrame) -> pd.DataFrame:
    if "review_status" not in df.columns:
        return df.copy()
    accepted_keywords = ["expert", "multiple", "practice guideline", "reviewed"]
    mask = df["review_status"].fillna("").astype(str).str.lower().apply(lambda x: any(k in x for k in accepted_keywords))
    return df[mask].copy()


def build_high_confidence_dataset_from_csv(input_csv_path: str, output_csv_path: str | None = None, mode: str = "hybrid", keep_metadata: bool = True) -> Tuple[pd.DataFrame, DatasetBuildReport]:
    raw_df = pd.read_csv(input_csv_path)
    raw_df = normalize_clinvar_dataframe(raw_df)
    raw_df = filter_high_confidence_variants(raw_df)
    built_df, report = build_dataset_from_dataframe(raw_df, mode=mode, keep_metadata=keep_metadata)
    if output_csv_path:
        built_df.to_csv(output_csv_path, index=False)
    return built_df, report


def summarize_dataset_cohort(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["group", "n_variants", "n_pathogenic_like", "n_benign_like", "has_conservation_data", "has_structure_data", "has_external_predictors"])
    predictor_cols = [c for c in ["revel", "bayesdel", "alphamissense", "cadd"] if c in df.columns]
    predictor_cols.extend([c for c in df.columns if c.startswith("feature_")])
    rows = []
    grouped = list(df.groupby("gene")) + [("combined", df.copy())]
    for group_name, subset in grouped:
        rows.append({
            "group": group_name,
            "n_variants": int(len(subset)),
            "n_pathogenic_like": int((subset["label"] == 1).sum()),
            "n_benign_like": int((subset["label"] == 0).sum()),
            "has_conservation_data": int((subset["has_conservation_data"] == 1).sum()) if "has_conservation_data" in subset.columns else 0,
            "has_structure_data": int((subset["has_structure_data"] == 1).sum()) if "has_structure_data" in subset.columns else 0,
            "has_external_predictors": int(subset[predictor_cols].notna().any(axis=1).sum()) if predictor_cols else 0,
        })
    return pd.DataFrame(rows)


def inspect_dataset_quality(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    outputs: Dict[str, pd.DataFrame] = {}
    if df.empty:
        outputs["missingness"] = pd.DataFrame(columns=["column", "missing_n", "missing_pct"])
        outputs["duplicates"] = pd.DataFrame(columns=["variant", "count"])
        outputs["class_balance"] = pd.DataFrame(columns=["group", "label", "count"])
        return outputs

    outputs["missingness"] = pd.DataFrame({
        "column": df.columns,
        "missing_n": [int(df[c].isna().sum()) for c in df.columns],
        "missing_pct": [float(df[c].isna().mean() * 100.0) for c in df.columns],
    }).sort_values(["missing_pct", "missing_n"], ascending=False).reset_index(drop=True)

    if "variant" in df.columns:
        dup = df.groupby("variant").size().reset_index(name="count").sort_values("count", ascending=False)
        outputs["duplicates"] = dup[dup["count"] > 1].reset_index(drop=True)
    else:
        outputs["duplicates"] = pd.DataFrame(columns=["variant", "count"])

    rows = []
    grouped = list(df.groupby("gene")) + [("combined", df.copy())] if "gene" in df.columns else [("combined", df.copy())]
    for group_name, subset in grouped:
        for label_value in sorted(subset["label"].dropna().unique().tolist()):
            rows.append({"group": group_name, "label": int(label_value), "count": int((subset["label"] == label_value).sum())})
    outputs["class_balance"] = pd.DataFrame(rows).reset_index(drop=True)
    return outputs


def export_dataset_quality_reports(quality_reports: Dict[str, pd.DataFrame], output_dir: str = "primevarclass_results") -> Dict[str, str]:
    os.makedirs(output_dir, exist_ok=True)
    paths: Dict[str, str] = {}
    for report_name, table in quality_reports.items():
        path = os.path.join(output_dir, f"dataset_quality_{report_name}.csv")
        table.to_csv(path, index=False)
        paths[report_name] = path
    return paths


def get_feature_subsets(df: pd.DataFrame) -> Dict[str, List[str]]:
    excluded = set(NON_FEATURE_METADATA_COLUMNS)
    excluded.update([c for c in df.columns if c.startswith("meta_")])
    available = [c for c in df.columns if c not in excluded]

    prime_features = [c for c in available if c.startswith("prime_") or c.startswith("codon_count") or c == "mass_prime_transition"]
    biochemical_features = [c for c in available if c.startswith("mass_") or c.startswith("hydro_") or c.startswith("charge_") or c in {"aa_ref", "aa_alt", "polar_switch", "aromatic_switch", "prime_mass_retention", "class_group_ref", "class_group_alt", "conservative_class_change", "biochemical_severity_score", "gene", "position"}]
    conservation_features = [c for c in available if c in {"phylop", "gerp", "siphy", "has_conservation_data", "conservation_signal_mean"}]
    structure_features = [c for c in available if c in {"rsa", "ddg_foldx", "functional_domain", "protein_interface", "distance_to_key_site", "has_structure_data", "structure_signal_mean", "in_functional_domain", "in_protein_interface"}]
    external_predictor_features = [c for c in available if c in {"revel", "bayesdel", "alphamissense", "cadd"} or c.startswith("feature_")]

    hybrid_features = sorted(set(prime_features) | set(biochemical_features))
    hybrid_conservation = sorted(set(hybrid_features) | set(conservation_features))
    hybrid_conservation_structure = sorted(set(hybrid_conservation) | set(structure_features))
    external_only = sorted(set(external_predictor_features))
    hybrid_plus_external = sorted(set(hybrid_conservation_structure) | set(external_predictor_features))

    return {
        "prime_only": [c for c in prime_features if c in df.columns],
        "biochemical_only": [c for c in biochemical_features if c in df.columns],
        "hybrid": [c for c in hybrid_features if c in df.columns],
        "hybrid_plus_conservation": [c for c in hybrid_conservation if c in df.columns],
        "hybrid_plus_conservation_structure": [c for c in hybrid_conservation_structure if c in df.columns],
        "external_predictors_only": [c for c in external_only if c in df.columns],
        "hybrid_plus_external": [c for c in hybrid_plus_external if c in df.columns],
    }


def normalize_model_family(value: str | None) -> str:
    key = MODEL_FAMILY_ALIASES.get(str(value or DEFAULT_MODEL_FAMILY).strip().lower().replace("-", "_"))
    if key not in SUPPORTED_MODEL_FAMILIES:
        raise ValueError(
            f"Familia de modelo nao suportada: {value}. Use uma entre {sorted(SUPPORTED_MODEL_FAMILIES)}."
        )
    return key


def resolve_model_families(model_families: List[str] | None = None) -> List[str]:
    families = model_families or [DEFAULT_MODEL_FAMILY]
    resolved: List[str] = []
    for family in families:
        normalized = normalize_model_family(family)
        if normalized not in resolved:
            resolved.append(normalized)
    return resolved


def make_experiment_name(feature_set_name: str, model_family: str) -> str:
    normalized_family = normalize_model_family(model_family)
    if normalized_family == DEFAULT_MODEL_FAMILY:
        return feature_set_name
    return f"{feature_set_name}__{normalized_family}"


def _build_estimator(model_family: str, random_state: int = 42):
    normalized_family = normalize_model_family(model_family)
    if normalized_family == "random_forest":
        return RandomForestClassifier(
            n_estimators=300,
            max_depth=None,
            min_samples_split=4,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=random_state,
            n_jobs=DEFAULT_PARALLEL_JOBS,
        )
    if normalized_family == "extra_trees":
        return ExtraTreesClassifier(
            n_estimators=400,
            max_depth=None,
            min_samples_split=3,
            min_samples_leaf=1,
            class_weight="balanced",
            random_state=random_state,
            n_jobs=DEFAULT_PARALLEL_JOBS,
        )
    if normalized_family == "logistic_regression":
        return LogisticRegression(
            class_weight="balanced",
            solver="liblinear",
            max_iter=2000,
            random_state=random_state,
        )
    if normalized_family == "xgboost":
        if not _HAS_XGBOOST:
            raise ImportError(
                "XGBoost nao esta instalado. Instale com: pip install xgboost>=2.0"
            )
        return XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=2,
            scale_pos_weight=1.0,
            use_label_encoder=False,
            eval_metric="logloss",
            random_state=random_state,
            n_jobs=DEFAULT_PARALLEL_JOBS,
            verbosity=0,
        )
    if normalized_family == "lightgbm":
        if not _HAS_LIGHTGBM:
            raise ImportError(
                "LightGBM nao esta instalado. Instale com: pip install lightgbm>=4.0"
            )
        return LGBMClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_samples=5,
            is_unbalance=True,
            random_state=random_state,
            n_jobs=DEFAULT_PARALLEL_JOBS,
            verbose=-1,
        )
    raise ValueError(f"Familia de modelo nao suportada: {model_family}")


def _build_pipeline(X: pd.DataFrame, random_state: int = 42, model_family: str = DEFAULT_MODEL_FAMILY) -> Pipeline:
    X = X.loc[:, [col for col in X.columns if not X[col].isna().all()]].copy()
    if X.empty:
        raise ValueError("Nenhuma feature observada permaneceu apos remover colunas totalmente ausentes.")
    numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = [c for c in X.columns if c not in numeric_cols]

    numeric_transformer = Pipeline(steps=[("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())])
    categorical_transformer = Pipeline(steps=[("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))])

    preprocessor = ColumnTransformer(transformers=[("num", numeric_transformer, numeric_cols), ("cat", categorical_transformer, categorical_cols)])
    model = _build_estimator(model_family=model_family, random_state=random_state)
    return Pipeline(steps=[("preprocessor", preprocessor), ("model", model)])


def _observed_feature_columns(df: pd.DataFrame, feature_columns: List[str]) -> List[str]:
    return [column for column in feature_columns if column in df.columns and not df[column].isna().all()]


def _fit_pipeline(X: pd.DataFrame, y: pd.Series, random_state: int = 42) -> Pipeline:
    X = X.loc[:, [col for col in X.columns if not X[col].isna().all()]].copy()
    if X.empty:
        raise ValueError("Nenhuma feature observada permaneceu apÃ³s remover colunas totalmente ausentes.")
    numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = [c for c in X.columns if c not in numeric_cols]

    numeric_transformer = Pipeline(steps=[("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())])
    categorical_transformer = Pipeline(steps=[("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))])

    preprocessor = ColumnTransformer(transformers=[("num", numeric_transformer, numeric_cols), ("cat", categorical_transformer, categorical_cols)])
    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_split=4,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=random_state,
        n_jobs=DEFAULT_PARALLEL_JOBS,
    )
    pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("model", model)])
    pipeline.fit(X, y)
    return pipeline


def _recommended_cv_splits(y: pd.Series, preferred_splits: int = 5) -> int:
    class_counts = pd.Series(y).value_counts()
    if class_counts.empty or int(class_counts.min()) < 2:
        raise ValueError("O treinamento exige pelo menos 2 variantes em cada classe.")
    return int(min(preferred_splits, class_counts.min()))


def train_baseline_model(df: pd.DataFrame) -> Tuple[Pipeline, dict]:
    if "label" not in df.columns:
        raise ValueError("O dataframe precisa conter a coluna 'label'.")
    X = df.drop(columns=[c for c in ["label", "variant"] if c in df.columns])
    y = df["label"].astype(int)
    pipeline = _fit_pipeline(X, y)

    cv_splits = _recommended_cv_splits(y)
    cv = StratifiedKFold(n_splits=cv_splits, shuffle=True, random_state=42)
    probas = cross_val_predict(pipeline, X, y, cv=cv, method="predict_proba")[:, 1]
    preds = (probas >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, preds).ravel()

    metrics = {
        "cv_folds": cv_splits,
        "auc_roc": roc_auc_score(y, probas),
        "auc_pr": average_precision_score(y, probas),
        "accuracy": accuracy_score(y, preds),
        "sensitivity": tp / (tp + fn) if (tp + fn) > 0 else np.nan,
        "specificity": tn / (tn + fp) if (tn + fp) > 0 else np.nan,
        "mcc": matthews_corrcoef(y, preds),
        "precision_at_0_5": tp / (tp + fp) if (tp + fp) > 0 else np.nan,
        "recall_at_0_5": tp / (tp + fn) if (tp + fn) > 0 else np.nan,
    }
    pipeline.fit(X, y)
    return pipeline, metrics


def train_model_with_feature_subset(df: pd.DataFrame, feature_columns: List[str]) -> Tuple[Pipeline, dict]:
    if not feature_columns:
        raise ValueError("Nenhuma feature foi selecionada para o experimento.")
    work_df = df[feature_columns + ["label"]].copy()
    work_df["variant"] = [f"row_{i}" for i in range(len(work_df))]
    return train_baseline_model(work_df)


def train_holdout_model(df: pd.DataFrame, feature_columns: List[str], test_size: float = 0.3, random_state: int = 42) -> Tuple[Pipeline, dict]:
    if not feature_columns:
        raise ValueError("Nenhuma feature foi selecionada para o experimento holdout.")
    X = df[feature_columns].copy()
    y = df["label"].astype(int)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state, stratify=y)
    pipeline = _fit_pipeline(X_train, y_train, random_state=random_state)
    probas = pipeline.predict_proba(X_test)[:, 1]
    preds = (probas >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, preds).ravel()
    metrics = {
        "auc_roc": roc_auc_score(y_test, probas),
        "auc_pr": average_precision_score(y_test, probas),
        "accuracy": accuracy_score(y_test, preds),
        "sensitivity": tp / (tp + fn) if (tp + fn) > 0 else np.nan,
        "specificity": tn / (tn + fp) if (tn + fp) > 0 else np.nan,
        "mcc": matthews_corrcoef(y_test, preds),
        "precision_at_0_5": tp / (tp + fp) if (tp + fp) > 0 else np.nan,
        "recall_at_0_5": tp / (tp + fn) if (tp + fn) > 0 else np.nan,
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
    }
    return pipeline, metrics


def summarize_feature_importance(pipeline: Pipeline, X: pd.DataFrame, y: pd.Series, top_n: int = 15) -> pd.DataFrame:
    result = permutation_importance(
        pipeline,
        X,
        y,
        n_repeats=10,
        random_state=42,
        n_jobs=DEFAULT_PARALLEL_JOBS,
        scoring="roc_auc",
    )
    importance_df = pd.DataFrame({"feature": X.columns, "importance_mean": result.importances_mean, "importance_std": result.importances_std})
    return importance_df.sort_values("importance_mean", ascending=False).head(top_n).reset_index(drop=True)


def run_experiment_suite(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame], Dict[str, Pipeline], Dict[str, List[str]]]:
    feature_sets = get_feature_subsets(df)
    metrics_rows = []
    importance_tables = {}
    trained_models = {}

    for experiment_name, cols in feature_sets.items():
        if not cols:
            continue
        model, metrics = train_model_with_feature_subset(df, cols)
        trained_models[experiment_name] = model
        metrics_rows.append({"experiment": experiment_name, "n_features": len(cols), **metrics})
        importance_tables[experiment_name] = summarize_feature_importance(model, df[cols].copy(), df["label"].astype(int))

    metrics_df = pd.DataFrame(metrics_rows)
    if not metrics_df.empty:
        metrics_df = metrics_df.sort_values(["auc_roc", "auc_pr", "mcc"], ascending=False)
    return metrics_df, importance_tables, trained_models, feature_sets


def run_gene_stratified_experiments(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    results = {}
    for gene_name in _iter_available_genes(df):
        subset = df[df["gene"] == gene_name].copy()
        if len(subset) >= 4 and subset["label"].nunique() == 2:
            metrics_df, _, _, _ = run_experiment_suite(subset)
            results[gene_name] = metrics_df
    if len(df) >= 4 and df["label"].nunique() == 2:
        metrics_df, _, _, _ = run_experiment_suite(df.copy())
        results["combined"] = metrics_df
    return results


def run_holdout_experiment_suite(df: pd.DataFrame, test_size: float = 0.3, random_state: int = 42) -> pd.DataFrame:
    feature_sets = get_feature_subsets(df)
    rows = []
    for experiment_name, cols in feature_sets.items():
        if not cols or len(df) < 10 or df["label"].nunique() < 2:
            continue
        _, metrics = train_holdout_model(df=df, feature_columns=cols, test_size=test_size, random_state=random_state)
        rows.append({"experiment": experiment_name, "evaluation": "holdout", "n_features": len(cols), **metrics})
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["auc_roc", "auc_pr", "mcc"], ascending=False)
    return out


def run_gene_holdout_experiments(df: pd.DataFrame, test_size: float = 0.3, random_state: int = 42) -> Dict[str, pd.DataFrame]:
    results = {}
    for gene_name in _iter_available_genes(df):
        subset = df[df["gene"] == gene_name].copy()
        if len(subset) >= 10 and subset["label"].nunique() == 2:
            results[gene_name] = run_holdout_experiment_suite(subset, test_size=test_size, random_state=random_state)
    if len(df) >= 10 and df["label"].nunique() == 2:
        results["combined"] = run_holdout_experiment_suite(df.copy(), test_size=test_size, random_state=random_state)
    return results


def run_repeated_holdout_experiment_suite(df: pd.DataFrame, test_size: float = 0.3, n_repeats: int = 10, random_state: int = 42) -> pd.DataFrame:
    feature_sets = get_feature_subsets(df)
    rows = []
    for experiment_name, cols in feature_sets.items():
        if not cols or len(df) < 10 or df["label"].nunique() < 2:
            continue
        repeat_metrics = []
        for i in range(n_repeats):
            _, metrics = train_holdout_model(df=df, feature_columns=cols, test_size=test_size, random_state=random_state + i)
            repeat_metrics.append(metrics)
        rep_df = pd.DataFrame(repeat_metrics)
        rows.append({
            "experiment": experiment_name,
            "evaluation": "repeated_holdout",
            "n_features": len(cols),
            "n_repeats": n_repeats,
            "auc_roc_mean": float(rep_df["auc_roc"].mean()),
            "auc_roc_std": float(rep_df["auc_roc"].std(ddof=1)) if len(rep_df) > 1 else 0.0,
            "auc_pr_mean": float(rep_df["auc_pr"].mean()),
            "auc_pr_std": float(rep_df["auc_pr"].std(ddof=1)) if len(rep_df) > 1 else 0.0,
            "mcc_mean": float(rep_df["mcc"].mean()),
            "mcc_std": float(rep_df["mcc"].std(ddof=1)) if len(rep_df) > 1 else 0.0,
            "accuracy_mean": float(rep_df["accuracy"].mean()),
            "accuracy_std": float(rep_df["accuracy"].std(ddof=1)) if len(rep_df) > 1 else 0.0,
        })
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["auc_roc_mean", "auc_pr_mean", "mcc_mean"], ascending=False)
    return out


def _fit_pipeline(
    X: pd.DataFrame,
    y: pd.Series,
    random_state: int = 42,
    model_family: str = DEFAULT_MODEL_FAMILY,
) -> Pipeline:
    pipeline = _build_pipeline(X=X, random_state=random_state, model_family=model_family)
    pipeline.fit(X, y)
    return pipeline


def train_baseline_model(df: pd.DataFrame, model_family: str = DEFAULT_MODEL_FAMILY) -> Tuple[Pipeline, dict]:
    if "label" not in df.columns:
        raise ValueError("O dataframe precisa conter a coluna 'label'.")
    X = df.drop(columns=[c for c in ["label", "variant"] if c in df.columns])
    y = df["label"].astype(int)
    pipeline = _build_pipeline(X, random_state=42, model_family=model_family)

    cv_splits = _recommended_cv_splits(y)
    cv = StratifiedKFold(n_splits=cv_splits, shuffle=True, random_state=42)
    probas = cross_val_predict(pipeline, X, y, cv=cv, method="predict_proba")[:, 1]
    preds = (probas >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, preds).ravel()

    metrics = {
        "cv_folds": cv_splits,
        "model_family": normalize_model_family(model_family),
        "auc_roc": roc_auc_score(y, probas),
        "auc_pr": average_precision_score(y, probas),
        "accuracy": accuracy_score(y, preds),
        "sensitivity": tp / (tp + fn) if (tp + fn) > 0 else np.nan,
        "specificity": tn / (tn + fp) if (tn + fp) > 0 else np.nan,
        "mcc": matthews_corrcoef(y, preds),
        "precision_at_0_5": tp / (tp + fp) if (tp + fp) > 0 else np.nan,
        "recall_at_0_5": tp / (tp + fn) if (tp + fn) > 0 else np.nan,
    }
    pipeline.fit(X, y)
    return pipeline, metrics


def train_model_with_feature_subset(
    df: pd.DataFrame,
    feature_columns: List[str],
    model_family: str = DEFAULT_MODEL_FAMILY,
) -> Tuple[Pipeline, dict]:
    observed_columns = _observed_feature_columns(df, feature_columns)
    if not observed_columns:
        raise ValueError("Nenhuma feature foi selecionada para o experimento.")
    work_df = df[observed_columns + ["label"]].copy()
    work_df["variant"] = [f"row_{i}" for i in range(len(work_df))]
    return train_baseline_model(work_df, model_family=model_family)


def train_holdout_model(
    df: pd.DataFrame,
    feature_columns: List[str],
    test_size: float = 0.3,
    random_state: int = 42,
    model_family: str = DEFAULT_MODEL_FAMILY,
) -> Tuple[Pipeline, dict]:
    observed_columns = _observed_feature_columns(df, feature_columns)
    if not observed_columns:
        raise ValueError("Nenhuma feature foi selecionada para o experimento holdout.")
    X = df[observed_columns].copy()
    y = df["label"].astype(int)
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )
    pipeline = _fit_pipeline(X_train, y_train, random_state=random_state, model_family=model_family)
    probas = pipeline.predict_proba(X_test)[:, 1]
    preds = (probas >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, preds).ravel()
    metrics = {
        "model_family": normalize_model_family(model_family),
        "auc_roc": roc_auc_score(y_test, probas),
        "auc_pr": average_precision_score(y_test, probas),
        "accuracy": accuracy_score(y_test, preds),
        "sensitivity": tp / (tp + fn) if (tp + fn) > 0 else np.nan,
        "specificity": tn / (tn + fp) if (tn + fp) > 0 else np.nan,
        "mcc": matthews_corrcoef(y_test, preds),
        "precision_at_0_5": tp / (tp + fp) if (tp + fp) > 0 else np.nan,
        "recall_at_0_5": tp / (tp + fn) if (tp + fn) > 0 else np.nan,
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
    }
    return pipeline, metrics


def build_experiment_specs(df: pd.DataFrame, model_families: List[str] | None = None) -> Tuple[List[dict], Dict[str, List[str]]]:
    feature_sets = get_feature_subsets(df)
    specs: List[dict] = []
    for feature_set_name, feature_columns in feature_sets.items():
        if not feature_columns:
            continue
        for model_family in resolve_model_families(model_families):
            specs.append(
                {
                    "experiment": make_experiment_name(feature_set_name, model_family),
                    "feature_set": feature_set_name,
                    "feature_columns": feature_columns,
                    "model_family": model_family,
                    "is_primary_experiment": int(normalize_model_family(model_family) == DEFAULT_MODEL_FAMILY),
                }
            )
    return specs, feature_sets


def run_experiment_suite(
    df: pd.DataFrame,
    model_families: List[str] | None = None,
) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame], Dict[str, Pipeline], Dict[str, List[str]]]:
    experiment_specs, _ = build_experiment_specs(df, model_families=model_families)
    metrics_rows = []
    importance_tables = {}
    trained_models = {}
    experiment_feature_sets: Dict[str, List[str]] = {}

    for spec in experiment_specs:
        experiment_name = spec["experiment"]
        feature_columns = _observed_feature_columns(df, spec["feature_columns"])
        if not feature_columns:
            continue
        model, metrics = train_model_with_feature_subset(df, feature_columns, model_family=spec["model_family"])
        trained_models[experiment_name] = model
        experiment_feature_sets[experiment_name] = list(feature_columns)
        metrics_rows.append(
            {
                "experiment": experiment_name,
                "feature_set": spec["feature_set"],
                "model_family": spec["model_family"],
                "is_primary_experiment": spec["is_primary_experiment"],
                "n_features": len(feature_columns),
                **metrics,
            }
        )
        importance_tables[experiment_name] = summarize_feature_importance(
            model,
            df[feature_columns].copy(),
            df["label"].astype(int),
        )

    metrics_df = pd.DataFrame(metrics_rows)
    if not metrics_df.empty:
        metrics_df = metrics_df.sort_values(
            ["auc_roc", "auc_pr", "mcc", "is_primary_experiment", "experiment"],
            ascending=[False, False, False, False, True],
        ).reset_index(drop=True)
    return metrics_df, importance_tables, trained_models, experiment_feature_sets


def run_gene_stratified_experiments(df: pd.DataFrame, model_families: List[str] | None = None) -> Dict[str, pd.DataFrame]:
    results = {}
    for gene_name in _iter_available_genes(df):
        subset = df[df["gene"] == gene_name].copy()
        if len(subset) >= 4 and subset["label"].nunique() == 2:
            metrics_df, _, _, _ = run_experiment_suite(subset, model_families=model_families)
            results[gene_name] = metrics_df
    if len(df) >= 4 and df["label"].nunique() == 2:
        metrics_df, _, _, _ = run_experiment_suite(df.copy(), model_families=model_families)
        results["combined"] = metrics_df
    return results


def run_holdout_experiment_suite(
    df: pd.DataFrame,
    test_size: float = 0.3,
    random_state: int = 42,
    model_families: List[str] | None = None,
) -> pd.DataFrame:
    experiment_specs, _ = build_experiment_specs(df, model_families=model_families)
    rows = []
    for spec in experiment_specs:
        experiment_name = spec["experiment"]
        feature_columns = _observed_feature_columns(df, spec["feature_columns"])
        if not feature_columns or len(df) < 10 or df["label"].nunique() < 2:
            continue
        _, metrics = train_holdout_model(
            df=df,
            feature_columns=feature_columns,
            test_size=test_size,
            random_state=random_state,
            model_family=spec["model_family"],
        )
        rows.append(
            {
                "experiment": experiment_name,
                "feature_set": spec["feature_set"],
                "model_family": spec["model_family"],
                "is_primary_experiment": spec["is_primary_experiment"],
                "evaluation": "holdout",
                "n_features": len(feature_columns),
                **metrics,
            }
        )
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(
            ["auc_roc", "auc_pr", "mcc", "is_primary_experiment", "experiment"],
            ascending=[False, False, False, False, True],
        ).reset_index(drop=True)
    return out


def run_gene_holdout_experiments(
    df: pd.DataFrame,
    test_size: float = 0.3,
    random_state: int = 42,
    model_families: List[str] | None = None,
) -> Dict[str, pd.DataFrame]:
    results = {}
    for gene_name in _iter_available_genes(df):
        subset = df[df["gene"] == gene_name].copy()
        if len(subset) >= 10 and subset["label"].nunique() == 2:
            results[gene_name] = run_holdout_experiment_suite(
                subset,
                test_size=test_size,
                random_state=random_state,
                model_families=model_families,
            )
    if len(df) >= 10 and df["label"].nunique() == 2:
        results["combined"] = run_holdout_experiment_suite(
            df.copy(),
            test_size=test_size,
            random_state=random_state,
            model_families=model_families,
        )
    return results


def run_repeated_holdout_experiment_suite(
    df: pd.DataFrame,
    test_size: float = 0.3,
    n_repeats: int = 10,
    random_state: int = 42,
    model_families: List[str] | None = None,
) -> pd.DataFrame:
    experiment_specs, _ = build_experiment_specs(df, model_families=model_families)
    rows = []
    for spec in experiment_specs:
        experiment_name = spec["experiment"]
        feature_columns = _observed_feature_columns(df, spec["feature_columns"])
        if not feature_columns or len(df) < 10 or df["label"].nunique() < 2:
            continue
        repeat_metrics = []
        for i in range(n_repeats):
            _, metrics = train_holdout_model(
                df=df,
                feature_columns=feature_columns,
                test_size=test_size,
                random_state=random_state + i,
                model_family=spec["model_family"],
            )
            repeat_metrics.append(metrics)
        rep_df = pd.DataFrame(repeat_metrics)
        rows.append(
            {
                "experiment": experiment_name,
                "feature_set": spec["feature_set"],
                "model_family": spec["model_family"],
                "is_primary_experiment": spec["is_primary_experiment"],
                "evaluation": "repeated_holdout",
                "n_features": len(feature_columns),
                "n_repeats": n_repeats,
                "auc_roc_mean": float(rep_df["auc_roc"].mean()),
                "auc_roc_std": float(rep_df["auc_roc"].std(ddof=1)) if len(rep_df) > 1 else 0.0,
                "auc_pr_mean": float(rep_df["auc_pr"].mean()),
                "auc_pr_std": float(rep_df["auc_pr"].std(ddof=1)) if len(rep_df) > 1 else 0.0,
                "mcc_mean": float(rep_df["mcc"].mean()),
                "mcc_std": float(rep_df["mcc"].std(ddof=1)) if len(rep_df) > 1 else 0.0,
                "accuracy_mean": float(rep_df["accuracy"].mean()),
                "accuracy_std": float(rep_df["accuracy"].std(ddof=1)) if len(rep_df) > 1 else 0.0,
            }
        )
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(
            ["auc_roc_mean", "auc_pr_mean", "mcc_mean", "is_primary_experiment", "experiment"],
            ascending=[False, False, False, False, True],
        ).reset_index(drop=True)
    return out


def bootstrap_metric_confidence_intervals(y_true: np.ndarray, y_score: np.ndarray, n_bootstrap: int = 1000, random_state: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(random_state)
    auc_rocs, auc_prs = [], []
    n = len(y_true)
    for _ in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        y_b = y_true[idx]
        s_b = y_score[idx]
        if len(np.unique(y_b)) < 2:
            continue
        auc_rocs.append(roc_auc_score(y_b, s_b))
        auc_prs.append(average_precision_score(y_b, s_b))

    def _ci(vals: List[float], metric_name: str) -> dict:
        if not vals:
            return {"metric": metric_name, "mean": np.nan, "ci_lower_95": np.nan, "ci_upper_95": np.nan, "n_bootstrap_valid": 0}
        arr = np.asarray(vals, dtype=float)
        return {
            "metric": metric_name,
            "mean": float(arr.mean()),
            "ci_lower_95": float(np.percentile(arr, 2.5)),
            "ci_upper_95": float(np.percentile(arr, 97.5)),
            "n_bootstrap_valid": int(len(arr)),
        }

    return pd.DataFrame([_ci(auc_rocs, "auc_roc"), _ci(auc_prs, "auc_pr")])


def compute_local_lr(tp: int, fp: int, fn: int, tn: int) -> float:
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else np.nan
    false_positive_rate = fp / (fp + tn) if (fp + tn) > 0 else np.nan
    if pd.isna(sensitivity) or pd.isna(false_positive_rate):
        return np.nan
    if false_positive_rate == 0:
        return np.inf
    return sensitivity / false_positive_rate


def classify_acmg_strength_from_lr(lr_value: float) -> str:
    if pd.isna(lr_value):
        return "uninformative"
    if lr_value == np.inf or lr_value >= ACMG_PATHOGENIC_LR_THRESHOLDS["strong"]:
        return "PP3_strong"
    if lr_value >= ACMG_PATHOGENIC_LR_THRESHOLDS["moderate"]:
        return "PP3_moderate"
    if lr_value >= ACMG_PATHOGENIC_LR_THRESHOLDS["supporting"]:
        return "PP3_supporting"
    if lr_value <= ACMG_BENIGN_LR_THRESHOLDS["strong"]:
        return "BP4_strong"
    if lr_value <= ACMG_BENIGN_LR_THRESHOLDS["moderate"]:
        return "BP4_moderate"
    if lr_value <= ACMG_BENIGN_LR_THRESHOLDS["supporting"]:
        return "BP4_supporting"
    return "uninformative"


def build_lr_calibration_table(y_true: pd.Series, y_score: np.ndarray, n_bins: int = 10) -> pd.DataFrame:
    calibration_df = pd.DataFrame({"y_true": y_true.astype(int), "y_score": y_score}).sort_values("y_score", ascending=False).reset_index(drop=True)
    calibration_df["bin"] = pd.qcut(calibration_df.index, q=min(n_bins, len(calibration_df)), duplicates="drop")
    rows = []
    total_pos = int((calibration_df["y_true"] == 1).sum())
    total_neg = int((calibration_df["y_true"] == 0).sum())

    for idx, (_, group) in enumerate(calibration_df.groupby("bin", observed=False)):
        tp = int((group["y_true"] == 1).sum())
        fp = int((group["y_true"] == 0).sum())
        fn = total_pos - tp
        tn = total_neg - fp
        lr = compute_local_lr(tp, fp, fn, tn)
        local_ppv = tp / (tp + fp) if (tp + fp) > 0 else np.nan
        rows.append({
            "bin_id": idx,
            "score_min": float(group["y_score"].min()),
            "score_max": float(group["y_score"].max()),
            "n_variants": len(group),
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "local_lr": lr,
            "local_ppv": local_ppv,
            "acmg_evidence": classify_acmg_strength_from_lr(lr),
        })
    return pd.DataFrame(rows).sort_values("score_max", ascending=False).reset_index(drop=True)


def calibrate_experiment_model(pipeline: Pipeline, df: pd.DataFrame, feature_columns: List[str], n_bins: int = 10) -> pd.DataFrame:
    X = df[feature_columns].copy()
    y = df["label"].astype(int)
    y_score = pipeline.predict_proba(X)[:, 1]
    return build_lr_calibration_table(y, y_score, n_bins=n_bins)


def run_acmg_calibration_suite(df: pd.DataFrame, trained_models: Dict[str, Pipeline], feature_sets: Dict[str, List[str]], n_bins: int = 10) -> Dict[str, pd.DataFrame]:
    calibration_tables = {}
    for experiment_name, model in trained_models.items():
        cols = feature_sets.get(experiment_name, [])
        if cols:
            calibration_tables[experiment_name] = calibrate_experiment_model(model, df, cols, n_bins=n_bins)
    return calibration_tables


def export_experiment_results(metrics_df: pd.DataFrame, importance_tables: Dict[str, pd.DataFrame], calibration_tables: Dict[str, pd.DataFrame] | None = None, output_dir: str = "primevarclass_results") -> Dict[str, str]:
    os.makedirs(output_dir, exist_ok=True)
    paths = {}
    metrics_path = os.path.join(output_dir, "experiment_metrics.csv")
    metrics_df.to_csv(metrics_path, index=False)
    paths["metrics"] = metrics_path
    for experiment_name, table in importance_tables.items():
        imp_path = os.path.join(output_dir, f"feature_importance_{experiment_name}.csv")
        table.to_csv(imp_path, index=False)
        paths[f"importance_{experiment_name}"] = imp_path
    if calibration_tables:
        for experiment_name, table in calibration_tables.items():
            cal_path = os.path.join(output_dir, f"acmg_calibration_{experiment_name}.csv")
            table.to_csv(cal_path, index=False)
            paths[f"calibration_{experiment_name}"] = cal_path
    return paths


def export_additional_evaluation_results(holdout_metrics: pd.DataFrame | None = None, repeated_holdout_metrics: pd.DataFrame | None = None, gene_holdout_metrics: Dict[str, pd.DataFrame] | None = None, bootstrap_ci_table: pd.DataFrame | None = None, output_dir: str = "primevarclass_results") -> Dict[str, str]:
    os.makedirs(output_dir, exist_ok=True)
    paths = {}
    if isinstance(holdout_metrics, pd.DataFrame) and not holdout_metrics.empty:
        path = os.path.join(output_dir, "holdout_metrics.csv")
        holdout_metrics.to_csv(path, index=False)
        paths["holdout_metrics"] = path
    if isinstance(repeated_holdout_metrics, pd.DataFrame) and not repeated_holdout_metrics.empty:
        path = os.path.join(output_dir, "repeated_holdout_metrics.csv")
        repeated_holdout_metrics.to_csv(path, index=False)
        paths["repeated_holdout_metrics"] = path
    if isinstance(gene_holdout_metrics, dict) and gene_holdout_metrics:
        for gene_name, table in gene_holdout_metrics.items():
            if isinstance(table, pd.DataFrame) and not table.empty:
                path = os.path.join(output_dir, f"holdout_metrics_{gene_name}.csv")
                table.to_csv(path, index=False)
                paths[f"holdout_metrics_{gene_name}"] = path
    if isinstance(bootstrap_ci_table, pd.DataFrame) and not bootstrap_ci_table.empty:
        path = os.path.join(output_dir, "bootstrap_confidence_intervals_best_experiment.csv")
        bootstrap_ci_table.to_csv(path, index=False)
        paths["bootstrap_ci_best_experiment"] = path
    return paths


def save_trained_models(
    models: Dict[str, Pipeline],
    output_dir: str = "primevarclass_results/models",
    feature_sets: Dict[str, List[str]] | None = None,
    metrics_df: pd.DataFrame | None = None,
    training_mode: str | None = None,
) -> Dict[str, str]:
    os.makedirs(output_dir, exist_ok=True)
    paths = {}
    for experiment_name, model in models.items():
        model_path = os.path.join(output_dir, f"{experiment_name}_model.joblib")
        joblib.dump(model, model_path)
        paths[experiment_name] = model_path
    if feature_sets:
        from .deployment import build_model_registry

        registry_outputs = build_model_registry(
            model_paths=paths,
            feature_sets=feature_sets,
            metrics_df=metrics_df,
            output_dir=output_dir,
            training_mode=training_mode,
        )
        paths["registry"] = registry_outputs["registry_path"]
    return paths


def build_interpretable_summary_report(results: dict) -> str:
    lines: List[str] = []
    lines.append("PrimeVarClass - Relatório Interpretável de Execução")
    lines.append("=" * 56)

    build_report = results.get("build_report")
    if build_report is not None and hasattr(build_report, "input_rows"):
        lines.append("\n1. Curadoria do dataset")
        lines.append(f"- Linhas de entrada: {build_report.input_rows}")
        lines.append(f"- Linhas válidas: {build_report.valid_rows}")
        lines.append(f"- Excluídas por campos ausentes: {build_report.excluded_missing}")
        lines.append(f"- Excluídas por gene inválido: {build_report.excluded_invalid_gene}")
        lines.append(f"- Excluídas por rótulo inválido: {build_report.excluded_invalid_label}")
        lines.append(f"- Excluídas por não serem missense: {build_report.excluded_non_missense}")

    cohort_summary = results.get("cohort_summary")
    if isinstance(cohort_summary, pd.DataFrame) and not cohort_summary.empty:
        lines.append("\n2. Resumo da coorte")
        for _, row in cohort_summary.iterrows():
            lines.append(
                f"- {row['group']}: n={int(row['n_variants'])}, "
                f"patogênicas-like={int(row['n_pathogenic_like'])}, "
                f"benignas-like={int(row['n_benign_like'])}, "
                f"conservação={int(row.get('has_conservation_data', 0))}, "
                f"estrutura={int(row.get('has_structure_data', 0))}, "
                f"preditores externos={int(row.get('has_external_predictors', 0))}"
            )

    metrics_df = results.get("metrics")
    if isinstance(metrics_df, pd.DataFrame) and not metrics_df.empty:
        best_row = metrics_df.iloc[0]
        lines.append("\n3. Melhor experimento")
        lines.append(f"- Experimento: {best_row['experiment']}")
        lines.append(f"- Nº de features: {int(best_row['n_features'])}")
        lines.append(f"- AUC-ROC: {float(best_row.get('auc_roc', np.nan)):.4f}")
        lines.append(f"- AUC-PR: {float(best_row.get('auc_pr', np.nan)):.4f}")
        lines.append(f"- MCC: {float(best_row.get('mcc', np.nan)):.4f}")
        lines.append("\n4. Ranking de experimentos")
        for _, row in metrics_df.iterrows():
            lines.append(f"- {row['experiment']}: AUC-ROC={float(row.get('auc_roc', np.nan)):.4f}, AUC-PR={float(row.get('auc_pr', np.nan)):.4f}, MCC={float(row.get('mcc', np.nan)):.4f}")

    holdout_metrics = results.get("holdout_metrics")
    if isinstance(holdout_metrics, pd.DataFrame) and not holdout_metrics.empty:
        lines.append("\n5. Avaliação holdout")
        for _, row in holdout_metrics.iterrows():
            lines.append(f"- {row['experiment']}: AUC-ROC={float(row.get('auc_roc', np.nan)):.4f}, AUC-PR={float(row.get('auc_pr', np.nan)):.4f}, MCC={float(row.get('mcc', np.nan)):.4f}, n_train={int(row.get('n_train', 0))}, n_test={int(row.get('n_test', 0))}")

    repeated_holdout_metrics = results.get("repeated_holdout_metrics")
    if isinstance(repeated_holdout_metrics, pd.DataFrame) and not repeated_holdout_metrics.empty:
        lines.append("\n6. Avaliação repeated holdout")
        for _, row in repeated_holdout_metrics.iterrows():
            lines.append(f"- {row['experiment']}: AUC-ROC={float(row.get('auc_roc_mean', np.nan)):.4f}±{float(row.get('auc_roc_std', np.nan)):.4f}, AUC-PR={float(row.get('auc_pr_mean', np.nan)):.4f}±{float(row.get('auc_pr_std', np.nan)):.4f}, MCC={float(row.get('mcc_mean', np.nan)):.4f}±{float(row.get('mcc_std', np.nan)):.4f}")

    bootstrap_ci_best_experiment = results.get("bootstrap_ci_best_experiment")
    if isinstance(bootstrap_ci_best_experiment, pd.DataFrame) and not bootstrap_ci_best_experiment.empty:
        lines.append("\n7. Intervalos de confiança bootstrap (melhor experimento)")
        for _, row in bootstrap_ci_best_experiment.iterrows():
            lines.append(f"- {row['metric']}: média={float(row.get('mean', np.nan)):.4f}, IC95%=[{float(row.get('ci_lower_95', np.nan)):.4f}, {float(row.get('ci_upper_95', np.nan)):.4f}], n_bootstrap_valid={int(row.get('n_bootstrap_valid', 0))}")

    importance_tables = results.get("importance_tables")
    if isinstance(importance_tables, dict) and importance_tables:
        lines.append("\n8. Principais features por experimento")
        for experiment_name, table in importance_tables.items():
            if isinstance(table, pd.DataFrame) and not table.empty:
                top_feats = ", ".join(table.head(5)["feature"].astype(str).tolist())
                lines.append(f"- {experiment_name}: {top_feats}")

    calibration_tables = results.get("calibration_tables")
    if isinstance(calibration_tables, dict) and calibration_tables:
        lines.append("\n9. Faixas ACMG/AMP informativas")
        for experiment_name, table in calibration_tables.items():
            if isinstance(table, pd.DataFrame) and not table.empty:
                informative = table[table["acmg_evidence"] != "uninformative"]
                lines.append(f"- {experiment_name}: {len(informative)}/{len(table)} bins informativos")

    return "\n".join(lines)


def export_interpretable_summary_report(results: dict, output_dir: str = "primevarclass_results") -> str:
    os.makedirs(output_dir, exist_ok=True)
    report_text = build_interpretable_summary_report(results)
    output_path = os.path.join(output_dir, "interpretable_summary_report.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    return output_path


def create_realistic_input_example(output_csv_path: str = "primevarclass_realistic_input_example.csv") -> str:
    example_df = pd.DataFrame([
        {"gene": "BRCA1", "hgvs_p": "p.Cys61Gly", "label": "Pathogenic", "review_status": "reviewed by expert panel", "source": "ClinVar", "clinical_significance": "Pathogenic", "variant_id": "cv_brca1_0001", "phylop": 7.8, "gerp": 5.9, "siphy": 11.4, "rsa": 0.05, "ddg_foldx": 2.6, "functional_domain": "RING", "protein_interface": "interface", "distance_to_key_site": 2.1, "revel": 0.97, "bayesdel": 0.71, "alphamissense": 0.99, "cadd": 29.4},
        {"gene": "BRCA1", "hgvs_p": "p.Met18Thr", "label": "Likely benign", "review_status": "criteria provided, multiple submitters, no conflicts", "source": "ClinVar", "clinical_significance": "Likely benign", "variant_id": "cv_brca1_0002", "phylop": 0.6, "gerp": 0.4, "siphy": 0.9, "rsa": 0.48, "ddg_foldx": 0.2, "functional_domain": "unknown", "protein_interface": "no", "distance_to_key_site": 17.3, "revel": 0.08, "bayesdel": -0.33, "alphamissense": 0.11, "cadd": 2.7},
        {"gene": "BRCA2", "hgvs_p": "p.Gly2508Ser", "label": "Likely pathogenic", "review_status": "criteria provided, multiple submitters, no conflicts", "source": "ClinVar", "clinical_significance": "Likely pathogenic", "variant_id": "cv_brca2_0001", "phylop": 6.1, "gerp": 4.8, "siphy": 8.6, "rsa": 0.13, "ddg_foldx": 1.7, "functional_domain": "DBD", "protein_interface": "interface", "distance_to_key_site": 4.9, "revel": 0.89, "bayesdel": 0.57, "alphamissense": 0.94, "cadd": 24.8},
        {"gene": "BRCA2", "hgvs_p": "p.Val2109Ile", "label": "Benign", "review_status": "criteria provided, multiple submitters, no conflicts", "source": "ClinVar", "clinical_significance": "Benign", "variant_id": "cv_brca2_0002", "phylop": 0.7, "gerp": 0.5, "siphy": 1.0, "rsa": 0.42, "ddg_foldx": 0.1, "functional_domain": "unknown", "protein_interface": "no", "distance_to_key_site": 19.8, "revel": 0.12, "bayesdel": -0.21, "alphamissense": 0.18, "cadd": 3.1},
        {"gene": "BRCA1", "hgvs_p": "p.Arg71Gly", "label": "Pathogenic", "review_status": "reviewed by expert panel", "source": "ClinVar", "clinical_significance": "Pathogenic", "variant_id": "cv_brca1_0003", "phylop": 8.1, "gerp": 6.2, "siphy": 12.7, "rsa": 0.07, "ddg_foldx": 2.9, "functional_domain": "RING", "protein_interface": "interface", "distance_to_key_site": 1.8, "revel": 0.98, "bayesdel": 0.73, "alphamissense": 0.99, "cadd": 30.2},
        {"gene": "BRCA2", "hgvs_p": "p.Asp2723His", "label": "Likely pathogenic", "review_status": "criteria provided, multiple submitters, no conflicts", "source": "ClinVar", "clinical_significance": "Likely pathogenic", "variant_id": "cv_brca2_0003", "phylop": 5.4, "gerp": 4.1, "siphy": 7.2, "rsa": 0.16, "ddg_foldx": 1.4, "functional_domain": "DBD", "protein_interface": "interface", "distance_to_key_site": 6.6, "revel": 0.84, "bayesdel": 0.48, "alphamissense": 0.91, "cadd": 22.3},
        {"gene": "BRCA1", "hgvs_p": "p.Ile21Val", "label": "Benign", "review_status": "criteria provided, multiple submitters, no conflicts", "source": "ClinVar", "clinical_significance": "Benign", "variant_id": "cv_brca1_0004", "phylop": 0.3, "gerp": 0.2, "siphy": 0.6, "rsa": 0.52, "ddg_foldx": 0.1, "functional_domain": "unknown", "protein_interface": "no", "distance_to_key_site": 21.4, "revel": 0.04, "bayesdel": -0.37, "alphamissense": 0.09, "cadd": 1.8},
        {"gene": "BRCA2", "hgvs_p": "p.Trp1692Cys", "label": "Pathogenic", "review_status": "reviewed by expert panel", "source": "ClinVar", "clinical_significance": "Pathogenic", "variant_id": "cv_brca2_0004", "phylop": 7.0, "gerp": 5.2, "siphy": 9.8, "rsa": 0.09, "ddg_foldx": 2.2, "functional_domain": "DBD", "protein_interface": "interface", "distance_to_key_site": 3.7, "revel": 0.95, "bayesdel": 0.69, "alphamissense": 0.97, "cadd": 28.0},
    ])
    example_df.to_csv(output_csv_path, index=False)
    return output_csv_path


def create_execution_manual(output_txt_path: str = "primevarclass_execution_manual.txt") -> str:
    manual = """PrimeVarClass - Manual rápido de execução

1. Estrutura mínima do CSV
   Colunas obrigatórias:
   - gene
   - hgvs_p
   - label

   Colunas opcionais recomendadas:
   - review_status
   - source
   - clinical_significance
   - variant_id
   - phylop, gerp, siphy
   - rsa, ddg_foldx, functional_domain, protein_interface, distance_to_key_site
   - revel, bayesdel, alphamissense, cadd

2. Exemplo de execução
   results = run_full_training_pipeline(
       input_csv_path='primevarclass_realistic_input_example.csv',
       mode='hybrid',
       output_dir='primevarclass_results',
       keep_metadata=True,
       high_confidence_only=True,
   )
"""
    with open(output_txt_path, "w", encoding="utf-8") as f:
        f.write(manual)
    return output_txt_path


def prepare_training_dataframe(raw_df: pd.DataFrame, mode: str = "hybrid", keep_metadata: bool = True, high_confidence_only: bool = False) -> Tuple[pd.DataFrame, DatasetBuildReport]:
    work_df = raw_df.copy()
    if high_confidence_only:
        work_df = normalize_clinvar_dataframe(work_df)
        work_df = filter_high_confidence_variants(work_df)
    return build_dataset_from_dataframe(work_df, mode=mode, keep_metadata=keep_metadata)


def _run_training_pipeline_from_built_dataset(
    built_df: pd.DataFrame,
    build_report: DatasetBuildReport,
    output_dir: str = "primevarclass_results",
    model_families: List[str] | None = None,
) -> dict:
    os.makedirs(output_dir, exist_ok=True)
    built_df.to_csv(f"{output_dir}/processed_dataset.csv", index=False)
    cohort_summary = summarize_dataset_cohort(built_df)
    cohort_summary.to_csv(f"{output_dir}/cohort_summary.csv", index=False)
    quality_reports = inspect_dataset_quality(built_df)
    quality_report_paths = export_dataset_quality_reports(quality_reports, output_dir=output_dir)

    experiment_metrics, importance_tables, trained_models, feature_sets = run_experiment_suite(
        built_df,
        model_families=model_families,
    )
    calibration_tables = run_acmg_calibration_suite(built_df, trained_models, feature_sets, n_bins=10)
    export_paths = export_experiment_results(experiment_metrics, importance_tables, calibration_tables=calibration_tables, output_dir=output_dir)
    training_mode = str(built_df["prime_mode"].dropna().iloc[0]) if "prime_mode" in built_df.columns and not built_df["prime_mode"].dropna().empty else None
    model_paths = save_trained_models(
        trained_models,
        output_dir=f"{output_dir}/models",
        feature_sets=feature_sets,
        metrics_df=experiment_metrics,
        training_mode=training_mode,
    )

    holdout_metrics = run_holdout_experiment_suite(built_df, model_families=model_families)
    repeated_holdout_metrics = run_repeated_holdout_experiment_suite(
        built_df,
        n_repeats=5,
        model_families=model_families,
    )
    gene_holdout_metrics = run_gene_holdout_experiments(built_df, model_families=model_families)

    bootstrap_ci_best_experiment = pd.DataFrame()
    if not experiment_metrics.empty:
        best_row = experiment_metrics.iloc[0]
        best_experiment = str(best_row["experiment"])
        best_features = feature_sets.get(best_experiment, [])
        best_model_family = str(best_row.get("model_family", DEFAULT_MODEL_FAMILY))
        if best_features and len(built_df) >= 10 and built_df["label"].nunique() == 2:
            best_model, _ = train_holdout_model(
                built_df,
                best_features,
                test_size=0.3,
                random_state=42,
                model_family=best_model_family,
            )
            X_all = built_df[best_features].copy()
            y_all = built_df["label"].astype(int).to_numpy()
            _, X_test, _, y_test = train_test_split(X_all, y_all, test_size=0.3, random_state=42, stratify=y_all)
            y_score = best_model.predict_proba(X_test)[:, 1]
            bootstrap_ci_best_experiment = bootstrap_metric_confidence_intervals(y_test, y_score, n_bootstrap=200, random_state=42)

    additional_export_paths = export_additional_evaluation_results(
        holdout_metrics=holdout_metrics,
        repeated_holdout_metrics=repeated_holdout_metrics,
        gene_holdout_metrics=gene_holdout_metrics,
        bootstrap_ci_table=bootstrap_ci_best_experiment,
        output_dir=output_dir,
    )

    report_path = os.path.join(output_dir, "build_report.json")
    pd.Series(asdict(build_report)).to_json(report_path, indent=2)

    results = {
        "build_report": build_report,
        "build_report_path": report_path,
        "n_rows_processed": len(built_df),
        "cohort_summary": cohort_summary,
        "quality_reports": quality_reports,
        "quality_report_paths": quality_report_paths,
        "metrics": experiment_metrics,
        "importance_tables": importance_tables,
        "calibration_tables": calibration_tables,
        "export_paths": export_paths,
        "additional_export_paths": additional_export_paths,
        "model_paths": model_paths,
        "holdout_metrics": holdout_metrics,
        "repeated_holdout_metrics": repeated_holdout_metrics,
        "gene_holdout_metrics": gene_holdout_metrics,
        "bootstrap_ci_best_experiment": bootstrap_ci_best_experiment,
    }
    summary_report_path = export_interpretable_summary_report(results, output_dir=output_dir)
    results["summary_report_path"] = summary_report_path
    return results


def print_usage_guide() -> None:
    print("\n=== Guia rápido de uso ===")
    print("1. Prepare um CSV com colunas mínimas: gene, hgvs_p, label")
    print("2. Opcionalmente adicione: review_status, source, phylop, gerp, siphy, rsa, ddg_foldx")
    print("3. Rode o pipeline completo com:")
    print("   results = run_full_training_pipeline('meu_dataset.csv', high_confidence_only=True)")
    print("4. Consulte os arquivos exportados em 'primevarclass_results/'")


def parse_cli_args():
    import argparse
    parser = argparse.ArgumentParser(description="PrimeVarClass - pipeline para classificação de variantes missense com expansão multigênica")
    parser.add_argument("--input-csv", type=str, default=None, help="Caminho para o CSV de entrada")
    parser.add_argument("--output-dir", type=str, default="primevarclass_results_cli", help="Diretório de saída")
    parser.add_argument("--mode", type=str, default="hybrid", choices=["codon", "prime_mass", "hybrid"], help="Modo de codificação prima")
    parser.add_argument("--high-confidence-only", action="store_true", help="Filtrar variantes de maior confiança")
    parser.add_argument("--demo", action="store_true", help="Executar a demo completa com CSV realista")
    return parser.parse_args()


def run_full_training_pipeline_from_dataframe(
    raw_df: pd.DataFrame,
    mode: str = "hybrid",
    output_dir: str = "primevarclass_results",
    keep_metadata: bool = True,
    high_confidence_only: bool = False,
    model_families: List[str] | None = None,
) -> dict:
    built_df, build_report = prepare_training_dataframe(
        raw_df=raw_df,
        mode=mode,
        keep_metadata=keep_metadata,
        high_confidence_only=high_confidence_only,
    )
    return _run_training_pipeline_from_built_dataset(
        built_df=built_df,
        build_report=build_report,
        output_dir=output_dir,
        model_families=model_families,
    )


def run_full_training_pipeline(
    input_csv_path: str,
    mode: str = "hybrid",
    output_dir: str = "primevarclass_results",
    keep_metadata: bool = True,
    high_confidence_only: bool = False,
    model_families: List[str] | None = None,
) -> dict:
    raw_df = pd.read_csv(input_csv_path)
    return run_full_training_pipeline_from_dataframe(
        raw_df=raw_df,
        mode=mode,
        output_dir=output_dir,
        keep_metadata=keep_metadata,
        high_confidence_only=high_confidence_only,
        model_families=model_families,
    )


def demo_dataset(mode: str = "hybrid") -> pd.DataFrame:
    variants = [
        "BRCA1 p.Cys61Gly", "BRCA1 p.Met18Thr", "BRCA1 p.Arg71Gly", "BRCA1 p.Val1736Ala",
        "BRCA2 p.Asp2723His", "BRCA2 p.Trp1692Cys", "BRCA2 p.Ala75Pro", "BRCA2 p.Lys3326Ter",
        "BRCA2 p.Gly2508Ser", "BRCA1 p.Ile21Val",
    ]
    labels = [1, 0, 1, 0, 1, 1, 0, 0, 1, 0]
    filtered_variants, filtered_labels = [], []
    for v, y in zip(variants, labels):
        try:
            parse_variant(v)
            filtered_variants.append(v)
            filtered_labels.append(y)
        except Exception:
            pass
    rows = []
    for i, v in enumerate(filtered_variants):
        parsed = parse_variant(v)
        feat = encode_variant_features(parsed, mode=mode)
        feat["variant"] = parsed.variant_str
        feat["label"] = filtered_labels[i]
        rows.append(feat)
    return pd.DataFrame(rows)


def compare_encoding_modes() -> pd.DataFrame:
    modes = ["codon", "prime_mass", "hybrid"]
    results = []
    for mode in modes:
        df_mode = demo_dataset(mode=mode)
        if len(df_mode) >= 8 and len(df_mode["label"].unique()) == 2:
            _, metrics = train_baseline_model(df_mode)
            metrics["mode"] = mode
            results.append(metrics)
    return pd.DataFrame(results)


def demo_real_dataset_builder(mode: str = "hybrid") -> Tuple[pd.DataFrame, DatasetBuildReport]:
    raw_df = dataset_schema_template()
    raw_df = pd.concat([raw_df, pd.DataFrame([
        {"gene": "BRCA2", "hgvs_p": "p.Lys3326Ter", "label": "Benign", "review_status": "multiple_submitters", "source": "ClinVar"},
        {"gene": "BRCA2", "hgvs_p": "p.Asp2723His", "label": "VUS", "review_status": "single_submitter", "source": "ClinVar"},
    ])], ignore_index=True)
    return build_dataset_from_dataframe(raw_df, mode=mode, keep_metadata=True)


def demo_full_pipeline_run(output_dir: str = "primevarclass_results_demo") -> dict:
    csv_path = create_realistic_input_example("primevarclass_realistic_input_example.csv")
    _ = create_execution_manual("primevarclass_execution_manual.txt")
    return run_full_training_pipeline(
        input_csv_path=csv_path,
        mode="hybrid",
        output_dir=output_dir,
        keep_metadata=True,
        high_confidence_only=True,
    )


def run_cli_entrypoint() -> dict:
    args = parse_cli_args()
    if args.demo or not args.input_csv:
        return demo_full_pipeline_run(output_dir=args.output_dir)
    return run_full_training_pipeline(
        input_csv_path=args.input_csv,
        mode=args.mode,
        output_dir=args.output_dir,
        keep_metadata=True,
        high_confidence_only=args.high_confidence_only,
    )


if __name__ == "__main__":
    print("=== Execução completa do pipeline com CSV realista ===")
    demo_results = demo_full_pipeline_run()
    print(f"Resumo interpretável salvo em: {demo_results.get('summary_report_path')}")
    print(f"Arquivos adicionais: {demo_results.get('additional_export_paths', {})}")
    print_usage_guide()
