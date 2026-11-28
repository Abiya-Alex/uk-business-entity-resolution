from scripts.analyze_charity_errors import (
    diagnostic_flags,
    features,
    postcode,
    similarity,
)


def test_normalized_similarity():
    assert similarity("Example Charity", "example charity") == 100
    assert similarity("", "Example Charity") is None
    assert postcode("tn9 1ab") == "TN91AB"


def test_matching_features():
    charity = {
        "name": "Example Charity",
        "address": "25 High Street",
        "postcode": "TN9 1AB",
    }

    company = {
        "name": "Example Charity",
        "address": "25 High Street",
        "postcode": "tn91ab",
    }

    values = features(charity, company)

    assert values["name_similarity"] == 100
    assert values["address_similarity"] == 100
    assert values["postcode_agreement"] is True

    assert diagnostic_flags(values) == [
        "no_clear_feature_disagreement"
    ]


def test_diagnostic_disagreements():
    values = {
        "name_similarity": 40,
        "address_similarity": 50,
        "postcode_agreement": False,
    }

    assert set(diagnostic_flags(values)) == {
        "low_name_similarity",
        "low_address_similarity",
        "postcode_disagreement",
    }


def test_missing_features():
    values = {
        "name_similarity": None,
        "address_similarity": None,
        "postcode_agreement": None,
    }

    assert set(diagnostic_flags(values)) == {
        "missing_name",
        "missing_address",
        "missing_postcode",
    }


def test_diagnostic_threshold_boundaries():
    values = {
        "name_similarity": 80,
        "address_similarity": 70,
        "postcode_agreement": True,
    }

    assert diagnostic_flags(values) == [
        "no_clear_feature_disagreement"
    ]
