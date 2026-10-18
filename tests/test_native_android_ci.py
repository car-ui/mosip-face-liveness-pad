import pytest

from scripts.run_native_android_ci import require_passed


def test_complete_android_success():
    require_passed("Time: 1.2\nOK (6 tests)\n\nINSTRUMENTATION_CODE: -1\n")


@pytest.mark.parametrize("output", [
    "INSTRUMENTATION_CODE: 0\n",
    "OK (6 tests)\n",
    "OK (5 tests)\nINSTRUMENTATION_CODE: -1\n",
    "OK (6 tests)\nFAILURES!!!\nINSTRUMENTATION_CODE: -1\n",
    "OK (6 tests)\nINSTRUMENTATION_FAILED: process crashed\nINSTRUMENTATION_CODE: -1\n",
    "OK (6 tests)\nINSTRUMENTATION_ABORTED\nINSTRUMENTATION_CODE: -1\n",
])
def test_exit_status_or_partial_output_cannot_claim_success(output):
    with pytest.raises(ValueError, match="complete passing"):
        require_passed(output)
