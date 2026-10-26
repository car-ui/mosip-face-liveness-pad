"""Select a research PAD threshold from a development-split evaluation report."""
import argparse
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.core.config import MIN_PASSIVE_THRESHOLD, MAX_PASSIVE_THRESHOLD


def metrics(rows, threshold):
    attacks = [row for row in rows if row["label"] == "attack"]
    bona_fide = [row for row in rows if row["label"] == "bona_fide"]
    apcer = sum(row["meanLiveScore"] >= threshold for row in attacks) / len(attacks)
    bpcer = sum(row["meanLiveScore"] < threshold for row in bona_fide) / len(bona_fide)
    return {"APCER": apcer, "BPCER": bpcer,
            "classifiedAttackClips": len(attacks), "classifiedBonaFideClips": len(bona_fide)}


def select_threshold(report, max_apcer, min_per_class):
    if (isinstance(max_apcer, bool) or not isinstance(max_apcer, (int, float))
            or not math.isfinite(max_apcer) or not 0 <= max_apcer <= 1):
        raise ValueError("Maximum APCER must be a finite value within 0..1")
    if isinstance(min_per_class, bool) or not isinstance(min_per_class, int) or min_per_class < 1:
        raise ValueError("Minimum class count must be a positive integer")
    if not isinstance(report, dict):
        raise ValueError("Input must be a JSON object")
    scope = report.get("scope", "")
    if not isinstance(scope, str):
        raise ValueError("Development report has an invalid scope")
    if report.get("dataSplit") != "development":
        raise ValueError("Threshold selection requires a development-split report")
    if report.get("splitAudit") != "subject_and_attack_source_groups_disjoint":
        raise ValueError("Development report lacks a passed participant and attack-source split audit")
    if "passive model only" not in scope.lower():
        raise ValueError("Input report is not a passive PAD evaluation")
    clips = report.get("clips")
    if not isinstance(clips, list) or not clips:
        raise ValueError("Development report has no clip rows")
    rows = []
    nonresponses = {"attack": 0, "bona_fide": 0}
    pai_counts = {}
    for row in clips:
        if not isinstance(row, dict):
            raise ValueError("Development report contains a malformed clip row")
        label = row.get("label")
        if label not in nonresponses:
            raise ValueError("Development report contains an unknown label")
        score = row.get("meanLiveScore")
        if score is None:
            nonresponses[label] += 1
            continue
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("Development report contains an invalid mean live score")
        pai = row.get("pai")
        if label == "attack" and (not isinstance(pai, str) or not pai.strip() or len(pai) > 128):
            raise ValueError("Development attack clips require a valid PAI group")
        normalized = {"label": label, "meanLiveScore": float(score), "pai": pai}
        rows.append(normalized)
        if label == "attack":
            pai_counts[normalized["pai"]] = pai_counts.get(normalized["pai"], 0) + 1

    attack_count = sum(row["label"] == "attack" for row in rows)
    bona_count = sum(row["label"] == "bona_fide" for row in rows)
    if attack_count < min_per_class or bona_count < min_per_class:
        raise ValueError("Too few classified clips: require at least {} per class, got attack={} bona_fide={}".format(
            min_per_class, attack_count, bona_count))

    # Calibration must return a threshold accepted by the runtime policy.
    scores = {MIN_PASSIVE_THRESHOLD, MAX_PASSIVE_THRESHOLD}
    for row in rows:
        value = row["meanLiveScore"]
        if MIN_PASSIVE_THRESHOLD <= value <= MAX_PASSIVE_THRESHOLD:
            scores.add(value)
        if value < MAX_PASSIVE_THRESHOLD:
            above = math.nextafter(value, 1.0)
            if MIN_PASSIVE_THRESHOLD <= above <= MAX_PASSIVE_THRESHOLD:
                scores.add(above)
    eligible = []
    for threshold in sorted(scores):
        result = metrics(rows, threshold)
        if result["APCER"] <= max_apcer:
            eligible.append((result["BPCER"], threshold, result))
    if not eligible:
        raise ValueError("No supported threshold meets the requested development APCER ceiling")
    # Within the APCER ceiling, minimize bona-fide rejections; prefer the lower
    # threshold when BPCER ties so the operating point is not stricter than needed.
    bpcer, threshold, result = min(eligible, key=lambda choice: (choice[0], choice[1]))
    groups = {}
    for pai in sorted(pai_counts):
        grouped = [row for row in rows if row["label"] == "attack" and row["pai"] == pai]
        groups[pai] = {"clips": len(grouped),
                       "accepted": sum(row["meanLiveScore"] >= threshold for row in grouped),
                       "APCER": sum(row["meanLiveScore"] >= threshold for row in grouped) / len(grouped)}
    return {
        "scope": "Development-set threshold selection only. Must be evaluated once on a held-out test split.",
        "dataSplit": "development",
        "modelHash": report.get("modelHash"),
        "threshold": threshold,
        "targetMaximumAPCER": max_apcer,
        "developmentMetrics": result,
        "nonresponsesExcludedFromRates": nonresponses,
        "attackGroups": groups,
        "minimumClassCount": min_per_class,
        "classifiedClipCounts": {"attack": attack_count, "bona_fide": bona_count},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("development_report", type=Path)
    parser.add_argument("--max-apcer", type=float, required=True,
                        help="Development APCER ceiling in 0..1 (for example, 0.05)")
    parser.add_argument("--minimum-per-class", type=int, default=20)
    parser.add_argument("--output", type=Path, default=Path("output/local/pad-threshold-selection.json"))
    args = parser.parse_args()
    if not math.isfinite(args.max_apcer) or not 0 <= args.max_apcer <= 1:
        parser.error("--max-apcer must be within 0..1")
    if args.minimum_per_class < 1:
        parser.error("--minimum-per-class must be positive")
    try:
        report = json.loads(args.development_report.read_text(encoding="utf-8"))
        result = select_threshold(report, args.max_apcer, args.minimum_per_class)
    except (OSError, json.JSONDecodeError, ValueError) as failure:
        parser.error(str(failure))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "threshold": result["threshold"],
                      "developmentMetrics": result["developmentMetrics"]}, indent=2))


if __name__ == "__main__":
    main()
