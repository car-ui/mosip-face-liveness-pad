from scripts.evaluate_dataset import summarize, validate_threshold
from scripts.select_pad_threshold import select_threshold
import math
import pytest


def test_pad_error_denominators_do_not_hide_nonresponses():
    rows = [{'label':'attack','accepted':True}, {'label':'attack','accepted':False},
            {'label':'attack','accepted':None}, {'label':'bona_fide','accepted':False},
            {'label':'bona_fide','accepted':None}]
    report = summarize(rows)
    assert report['APCER'] == .5
    assert report['BPCER'] == 1
    assert report['attack']['nonResponses'] == 1
    assert report['bona_fide']['nonResponses'] == 1
    assert summarize([])['APCER'] is None


def test_development_calibration_respects_apcer_ceiling_and_nonresponses():
    report = {
        "scope": "Passive model only. Mean valid-frame score per clip.",
        "dataSplit": "development",
        "splitAudit": "subject_and_attack_source_groups_disjoint",
        "modelHash": "fixture",
        "clips": [
            {"label": "attack", "pai": "print", "meanLiveScore": .8},
            {"label": "attack", "pai": "print", "meanLiveScore": .7},
            {"label": "attack", "pai": "screen", "meanLiveScore": None},
            {"label": "bona_fide", "pai": "bona_fide", "meanLiveScore": .9},
            {"label": "bona_fide", "pai": "bona_fide", "meanLiveScore": .6},
            {"label": "bona_fide", "pai": "bona_fide", "meanLiveScore": None},
        ],
    }
    result = select_threshold(report, max_apcer=.5, min_per_class=2)
    assert result["threshold"] == math.nextafter(.7, 1.0)
    assert result["developmentMetrics"]["APCER"] == .5
    assert result["developmentMetrics"]["BPCER"] == .5
    assert result["nonresponsesExcludedFromRates"] == {"attack": 1, "bona_fide": 1}


def test_selected_threshold_stays_inside_runtime_policy_range():
    report = {
        "scope": "Passive model only. Mean valid-frame score per clip.",
        "dataSplit": "development",
        "splitAudit": "subject_and_attack_source_groups_disjoint",
        "clips": [
            {"label": "attack", "pai": "print", "meanLiveScore": .1},
            {"label": "bona_fide", "pai": "bona_fide", "meanLiveScore": .2},
        ],
    }
    result = select_threshold(report, max_apcer=0, min_per_class=1)
    assert result["threshold"] == .46
    assert validate_threshold(result["threshold"]) == .46


def test_calibration_fails_when_only_unsupported_thresholds_meet_apcer():
    report = {
        "scope": "Passive model only. Mean valid-frame score per clip.",
        "dataSplit": "development",
        "splitAudit": "subject_and_attack_source_groups_disjoint",
        "clips": [
            {"label": "attack", "pai": "screen", "meanLiveScore": .995},
            {"label": "bona_fide", "pai": "bona_fide", "meanLiveScore": .8},
        ],
    }
    with pytest.raises(ValueError, match="No supported threshold"):
        select_threshold(report, max_apcer=0, min_per_class=1)


@pytest.mark.parametrize("threshold", [.459999, .990001, float("nan"), float("inf")])
def test_evaluator_rejects_thresholds_outside_runtime_policy_range(threshold):
    with pytest.raises(ValueError, match="supported range"):
        validate_threshold(threshold)


@pytest.mark.parametrize("threshold", [.46, .82, .99])
def test_evaluator_accepts_runtime_policy_threshold_boundaries(threshold):
    assert validate_threshold(threshold) == threshold


def test_threshold_calibration_rejects_test_split_and_small_classes():
    report = {"scope": "Passive model only.", "dataSplit": "test",
              "splitAudit": "subject_and_attack_source_groups_disjoint", "clips": []}
    try:
        select_threshold(report, max_apcer=.05, min_per_class=1)
        raise AssertionError("test split used for threshold calibration")
    except ValueError as expected:
        assert "development" in str(expected)

    report["dataSplit"] = "development"
    try:
        select_threshold(report, max_apcer=.05, min_per_class=1)
        raise AssertionError("empty development report accepted")
    except ValueError as expected:
        assert "no clip rows" in str(expected)


def test_threshold_calibration_requires_split_audit_and_valid_limits():
    report = {"scope": "Passive model only.", "dataSplit": "development", "clips": []}
    try:
        select_threshold(report, max_apcer=.05, min_per_class=1)
        raise AssertionError("unaudited development report accepted")
    except ValueError as expected:
        assert "split audit" in str(expected)

    report["splitAudit"] = "subject_and_attack_source_groups_disjoint"
    for apcer, minimum in ((float("nan"), 1), (.05, True), (1.1, 1), (.05, 0)):
        try:
            select_threshold(report, max_apcer=apcer, min_per_class=minimum)
            raise AssertionError("invalid threshold-selection limits accepted")
        except ValueError as expected:
            assert "APCER" in str(expected) or "class count" in str(expected)
