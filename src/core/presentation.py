"""Stable instructions and honest stage progress shared by local interfaces."""
from .config import ChallengeType
from .pipeline import PipelineState


ACTION_INSTRUCTIONS = {
    ChallengeType.BLINK: "Blink once, then open your eyes",
    ChallengeType.SMILE: "Smile naturally",
    ChallengeType.TURN_LEFT: "Turn slightly to YOUR LEFT, then face camera",
    ChallengeType.TURN_RIGHT: "Turn slightly to YOUR RIGHT, then face camera",
    ChallengeType.LOOK_UP: "Look slightly up, then face camera",
    ChallengeType.LOOK_DOWN: "Look slightly down, then face camera",
}


def stage_progress(result):
    if result.state == PipelineState.CAPTURE_SUCCESS:
        return 1.0, "Done"
    required = max(1, result.required_actions)
    completed = min(required, max(0, result.completed_actions))
    return completed / required, f"{completed}/{required}"


def stable_prompt(result):
    if result.state == PipelineState.ACTIVE_CHALLENGE and result.active_challenge:
        return ACTION_INSTRUCTIONS.get(result.active_challenge.challenge, "Follow the instruction")
    if result.state == PipelineState.PASSIVE_LIVENESS:
        return "Rechecking liveness" if result.restart_count else "Checking liveness"
    if result.state == PipelineState.FACE_DETECTION and result.quality is not None:
        return "Position your face"
    return result.status_text
