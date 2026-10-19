"""Prepared native copies must match the source that will be packaged."""
from pathlib import Path

import pytest

from scripts.verify_native_preparation import digest, expected_files, verify_copies


def write(path, content=b"fixture\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def prepared_fixture(tmp_path, platform):
    root, checkout = tmp_path / "source", tmp_path / "checkout"
    base = root / "integrations/native"
    for group in ("common", platform):
        write(base / group / "io/mosip/facepad" / (group + ".java"))
    if platform in ("android", "camera-sbi"):
        group = "android-test" if platform == "android" else "camera-sbi-test"
        write(base / group / "io/mosip/facepad/AcceptanceTest.java")
    if platform == "camera-sbi":
        write(base / "camera-sbi-debug/AndroidManifest.xml")
        write(base / "camera-sbi-debug/java/io/mosip/facepad/DebugActivity.java")
    pairs = expected_files(root, platform, checkout)
    for source, target in pairs:
        if not source.exists():
            write(source, b"binary\x00\r\nfixture" if source.suffix == ".onnx" else b"fixture\n")
        write(target, source.read_bytes())
    return root, checkout, pairs


@pytest.mark.parametrize("platform", ["desktop", "android", "camera-sbi"])
def test_matching_prepared_source_and_assets_pass(tmp_path, platform):
    root, checkout, pairs = prepared_fixture(tmp_path, platform)
    records, mismatches = verify_copies(root, platform, checkout)
    assert mismatches == []
    assert len(records) == len(pairs)
    assert len({item["path"] for item in records}) == len(records)
    assert all(len(item["sha256"]) == 64 for item in records)


@pytest.mark.parametrize("kind", ["missing-java", "stale-java", "stale-model"])
def test_missing_or_stale_copy_is_reported(tmp_path, kind):
    root, checkout, pairs = prepared_fixture(tmp_path, "desktop")
    suffix = ".onnx" if kind == "stale-model" else ".java"
    _, target = next(pair for pair in pairs if pair[0].suffix == suffix)
    if kind == "missing-java":
        target.unlink()
    else:
        target.write_bytes(b"old content")
    records, mismatches = verify_copies(root, "desktop", checkout)
    assert mismatches == [target.relative_to(checkout).as_posix()]
    assert len(records) == len(pairs)


def test_java_line_endings_normalize_but_binary_bytes_do_not(tmp_path):
    lf_java, crlf_java = tmp_path / "lf.java", tmp_path / "crlf.java"
    lf_model, crlf_model = tmp_path / "lf.onnx", tmp_path / "crlf.onnx"
    for path in (lf_java, lf_model):
        write(path, b"first\nsecond\n")
    for path in (crlf_java, crlf_model):
        write(path, b"first\r\nsecond\r\n")
    assert digest(lf_java) == digest(crlf_java)
    assert digest(lf_model) != digest(crlf_model)


@pytest.mark.parametrize("platform,group", [
    ("desktop", "common"), ("desktop", "desktop"),
    ("android", "android-test"), ("camera-sbi", "camera-sbi-test"),
    ("camera-sbi", "camera-sbi-debug"),
])
def test_empty_required_source_group_fails(tmp_path, platform, group):
    root, checkout, _ = prepared_fixture(tmp_path, platform)
    group_path = root / "integrations/native" / group
    for path in group_path.rglob("*"):
        if path.is_file():
            path.unlink()
    with pytest.raises(ValueError, match="Native source group is empty: " + group):
        expected_files(root, platform, checkout)


def test_wrong_source_root_does_not_silently_verify_zero_files(tmp_path):
    with pytest.raises(ValueError, match="Native source group is empty: common"):
        verify_copies(tmp_path / "wrong-root", "desktop", tmp_path / "checkout")
