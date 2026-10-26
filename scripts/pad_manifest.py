"""Validate a private, subject-disjoint PAD evaluation manifest."""

import json
import os
from pathlib import Path, PureWindowsPath


class ManifestError(ValueError):
    """Raised when an evaluation manifest cannot support a valid split."""


SPLIT_AUDIT = "subject_and_attack_source_groups_disjoint"


def _group_id(entry, field, line_number, required=True):
    value = entry.get(field)
    if value is None and not required:
        return None
    if (not isinstance(value, str) or not value or value != value.strip()
            or len(value) > 128):
        raise ManifestError("line {} requires a valid {} pseudonym".format(line_number, field))
    return value


def load_private_manifest(manifest_path):
    """Load and validate both splits; return private rows with resolved video paths.

    The input manifest must stay private. Group pseudonyms are used to verify
    non-overlap and are deliberately not copied into evaluation reports.
    """
    try:
        manifest_path = Path(manifest_path).resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as failure:
        raise ManifestError("manifest path cannot be resolved") from failure
    if not manifest_path.is_file():
        raise ManifestError("manifest path must name a regular file")
    try:
        root = manifest_path.parent.resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as failure:
        raise ManifestError("manifest folder cannot be resolved") from failure
    rows = []
    seen_paths = set()
    subject_splits = {}
    attack_source_splits = {}
    classes_by_split = {"development": set(), "test": set()}

    for line_number, raw_line in enumerate(manifest_path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw_line.strip():
            continue
        try:
            entry = json.loads(raw_line)
        except json.JSONDecodeError as failure:
            raise ManifestError("line {} is not valid JSON: {}".format(line_number, failure.msg))
        if not isinstance(entry, dict):
            raise ManifestError("line {} must be a JSON object".format(line_number))

        raw_path = entry.get("path")
        if (not isinstance(raw_path, str) or not raw_path or raw_path != raw_path.strip()
                or Path(raw_path).is_absolute() or PureWindowsPath(raw_path).is_absolute()
                or PureWindowsPath(raw_path).drive or "\x00" in raw_path
                or ".." in Path(raw_path).parts or ".." in PureWindowsPath(raw_path).parts):
            raise ManifestError("line {} path must be relative and stay inside the manifest folder".format(line_number))
        try:
            video_path = (root / Path(raw_path)).resolve(strict=True)
        except (OSError, RuntimeError, ValueError) as failure:
            raise ManifestError("line {} video path cannot be resolved".format(line_number)) from failure
        if root not in video_path.parents or not video_path.is_file():
            raise ManifestError("line {} path must resolve to a file inside the manifest folder".format(line_number))
        path_key = os.path.normcase(str(video_path))
        if path_key in seen_paths:
            raise ManifestError("line {} repeats a clip path".format(line_number))
        seen_paths.add(path_key)

        label = entry.get("label")
        split = entry.get("split")
        if label not in ("attack", "bona_fide"):
            raise ManifestError("line {} label must be attack or bona_fide".format(line_number))
        if not isinstance(split, str) or split not in classes_by_split:
            raise ManifestError("line {} split must be development or test".format(line_number))
        subject_group = _group_id(entry, "subject_group", line_number)
        subject_splits.setdefault(subject_group, set()).add(split)
        classes_by_split[split].add(label)

        pai = entry.get("pai", "bona_fide")
        attack_source_group = None
        if label == "attack":
            if not isinstance(pai, str) or not pai or pai != pai.strip() or len(pai) > 128:
                raise ManifestError("line {} attack requires a valid PAI group".format(line_number))
            attack_source_group = _group_id(entry, "attack_source_group", line_number)
            attack_source_splits.setdefault(attack_source_group, set()).add(split)
        elif "attack_source_group" in entry:
            raise ManifestError("line {} bona_fide rows cannot name an attack source".format(line_number))

        rows.append({"path": video_path, "label": label, "split": split,
                     "pai": pai, "subject_group": subject_group,
                     "attack_source_group": attack_source_group})

    if not rows:
        raise ManifestError("manifest contains no clips")
    for split, labels in classes_by_split.items():
        if labels != {"attack", "bona_fide"}:
            raise ManifestError("{} split must contain attack and bona_fide clips".format(split))
    if any(len(splits) > 1 for splits in subject_splits.values()):
        raise ManifestError("participant pseudonyms must not appear in both development and test splits")
    if any(len(splits) > 1 for splits in attack_source_splits.values()):
        raise ManifestError("attack-source pseudonyms must not appear in both development and test splits")
    return rows
