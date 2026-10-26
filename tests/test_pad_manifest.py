import json
from pathlib import Path, PureWindowsPath

import pytest

from scripts.pad_manifest import ManifestError, SPLIT_AUDIT, load_private_manifest


def _valid_rows():
    return [
        {"path": "clips/dev-live.mp4", "label": "bona_fide", "split": "development",
         "subject_group": "subject-dev"},
        {"path": "clips/dev-print.mp4", "label": "attack", "pai": "print",
         "attack_source_group": "print-source-dev", "split": "development",
         "subject_group": "subject-dev"},
        {"path": "clips/test-live.mp4", "label": "bona_fide", "split": "test",
         "subject_group": "subject-test"},
        {"path": "clips/test-print.mp4", "label": "attack", "pai": "print",
         "attack_source_group": "print-source-test", "split": "test",
         "subject_group": "subject-test"},
    ]


def _write_manifest(tmp_path, rows):
    clip_dir = tmp_path / "clips"
    clip_dir.mkdir(exist_ok=True)
    for row in rows:
        relative_path = Path(row["path"])
        if (relative_path.is_absolute() or PureWindowsPath(row["path"]).is_absolute()
                or PureWindowsPath(row["path"]).drive or ".." in relative_path.parts
                or ".." in PureWindowsPath(row["path"]).parts or "\x00" in row["path"]):
            continue
        clip = tmp_path / relative_path
        clip.parent.mkdir(parents=True, exist_ok=True)
        clip.write_bytes(b"fixture placeholder; loader checks manifest integrity only")
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    return manifest


def test_private_manifest_accepts_both_disjoint_splits_without_exporting_ids(tmp_path):
    rows = load_private_manifest(_write_manifest(tmp_path, _valid_rows()))

    assert len(rows) == 4
    assert {row["split"] for row in rows} == {"development", "test"}
    assert all(row["path"].is_absolute() for row in rows)
    assert SPLIT_AUDIT == "subject_and_attack_source_groups_disjoint"


def test_private_manifest_rejects_participant_overlap_between_splits(tmp_path):
    rows = _valid_rows()
    rows[2]["subject_group"] = "subject-dev"

    with pytest.raises(ManifestError, match="participant pseudonyms"):
        load_private_manifest(_write_manifest(tmp_path, rows))


def test_private_manifest_rejects_attack_source_overlap_between_splits(tmp_path):
    rows = _valid_rows()
    rows[3]["attack_source_group"] = "print-source-dev"

    with pytest.raises(ManifestError, match="attack-source pseudonyms"):
        load_private_manifest(_write_manifest(tmp_path, rows))


@pytest.mark.parametrize("field", ["subject_group", "attack_source_group"])
def test_private_manifest_requires_pseudonymous_groups(tmp_path, field):
    rows = _valid_rows()
    if field == "subject_group":
        rows[0].pop(field)
    else:
        rows[1].pop(field)

    with pytest.raises(ManifestError, match="pseudonym"):
        load_private_manifest(_write_manifest(tmp_path, rows))


@pytest.mark.parametrize("unsafe_path", ["../outside.mp4", "C:\\outside.mp4", "\\\\server\\share\\clip.mp4", "bad\x00clip.mp4"])
def test_private_manifest_rejects_absolute_and_traversal_paths(tmp_path, unsafe_path):
    rows = _valid_rows()
    rows[0]["path"] = unsafe_path

    with pytest.raises(ManifestError, match="relative"):
        load_private_manifest(_write_manifest(tmp_path, rows))


def test_private_manifest_requires_both_classes_in_both_splits(tmp_path):
    rows = [row for row in _valid_rows() if row["split"] != "test" or row["label"] != "attack"]

    with pytest.raises(ManifestError, match="test split must contain"):
        load_private_manifest(_write_manifest(tmp_path, rows))


def test_private_manifest_rejects_duplicate_clip_paths(tmp_path):
    rows = _valid_rows()
    rows[1]["path"] = rows[0]["path"]

    with pytest.raises(ManifestError, match="repeats a clip path"):
        load_private_manifest(_write_manifest(tmp_path, rows))
