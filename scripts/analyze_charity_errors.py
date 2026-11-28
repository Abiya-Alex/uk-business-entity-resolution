"""Reproducible feature-level diagnostics for linkage errors."""

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from rapidfuzz import fuzz


def load(path):
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def normalize(value):
    value = unicodedata.normalize("NFKC", value or "").casefold()
    return " ".join(re.findall(r"\w+", value))


def postcode(value):
    return re.sub(r"\s+", "", value or "").upper()


def similarity(left, right):
    left, right = normalize(left), normalize(right)
    if not left or not right:
        return None
    return round(fuzz.token_sort_ratio(left, right), 2)


def features(charity, company):
    name = similarity(charity.get("name"), company.get("name"))
    address = similarity(
        charity.get("address"), company.get("address")
    )

    cp = postcode(charity.get("postcode"))
    bp = postcode(company.get("postcode"))

    return {
        "name_similarity": name,
        "address_similarity": address,
        "postcode_agreement": cp == bp if cp and bp else None,
    }


def diagnostic_flags(values):
    flags = []

    name = values["name_similarity"]
    address = values["address_similarity"]
    agreement = values["postcode_agreement"]

    if name is None:
        flags.append("missing_name")
    elif name < 80:
        flags.append("low_name_similarity")

    if address is None:
        flags.append("missing_address")
    elif address < 70:
        flags.append("low_address_similarity")

    if agreement is None:
        flags.append("missing_postcode")
    elif not agreement:
        flags.append("postcode_disagreement")

    if not flags:
        flags.append("no_clear_feature_disagreement")

    return flags


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()

    base = args.directory

    charities = {
        row["id"]: row for row in load(base / "charities.csv")
    }
    companies = {
        row["id"]: row for row in load(base / "companies.csv")
    }
    errors = load(base / "errors-private.csv")

    reasons = Counter()
    flags = Counter()
    flags_by_reason = defaultdict(Counter)
    feature_scores = defaultdict(list)
    competitor_flags = Counter()
    unresolved = 0
    reference_pairs = 0
    competitor_pairs = 0

    for error in errors:
        reason = error["reason"]
        reasons[reason] += 1

        charity = charities.get(error["charity_id"])
        reference = companies.get(error["reference_company"])

        if charity is None:
            unresolved += 1
            continue

        if reference is None:
            flags["reference_unavailable"] += 1
            flags_by_reason[reason]["reference_unavailable"] += 1
        else:
            reference_pairs += 1
            values = features(charity, reference)

            for flag in diagnostic_flags(values):
                flags[flag] += 1
                flags_by_reason[reason][flag] += 1

            for key in ("name_similarity", "address_similarity"):
                if values[key] is not None:
                    feature_scores[key].append(values[key])

        if reason == "extra_auto_matches":
            raw = error.get("predicted_company_ids") or ""

            tokens = set(re.findall(r"[A-Za-z0-9]+", raw))
            tokens.discard(error["reference_company"])

            for candidate_id in sorted(tokens):
                candidate = companies.get(candidate_id)

                if candidate is None:
                    continue

                competitor_pairs += 1
                values = features(charity, candidate)

                if (values["name_similarity"] or 0) >= 80:
                    competitor_flags["similar_name"] += 1

                if (values["address_similarity"] or 0) >= 80:
                    competitor_flags["similar_address"] += 1

                if values["postcode_agreement"] is True:
                    competitor_flags["same_postcode"] += 1

    report = {
        "method": "deterministic feature-level diagnostics",
        "error_entries": len(errors),
        "unique_error_queries": len({
            row["charity_id"] for row in errors
        }),
        "error_categories": dict(reasons),
        "reference_pairs_analysed": reference_pairs,
        "diagnostic_flags": dict(flags),
        "flags_by_error_category": {
            key: dict(value)
            for key, value in flags_by_reason.items()
        },
        "mean_reference_similarity": {
            key: round(mean(values), 2)
            for key, values in feature_scores.items()
            if values
        },
        "competing_pairs_analysed": competitor_pairs,
        "competitor_flags": dict(competitor_flags),
        "unresolved_charity_ids": unresolved,
        "diagnostic_thresholds": {
            "low_name_similarity": 80,
            "low_address_similarity": 70,
            "high_competitor_similarity": 80,
        },
        "limitations": (
            "Flags can overlap. Similarity measures are diagnostic "
            "heuristics, not the original matcher scores or verified "
            "root causes. No manual adjudication was performed."
        ),
    }

    output = json.dumps(report, indent=2)

    (base / "error-diagnostics.json").write_text(
        output + "\n", encoding="utf-8"
    )

    print(output)


if __name__ == "__main__":
    main()
