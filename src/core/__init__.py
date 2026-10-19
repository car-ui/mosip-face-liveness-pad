from .config import LivenessConfig, WorkflowType, WorkflowPolicy, ChallengeType, LivenessDecision
from importlib import import_module

# Configuration and offline update tools should not initialize camera/model libraries.
_EXPORT_MODULES = {
    **dict.fromkeys(("FaceQualityAssessor", "DetectedFace", "QualityMetrics"), "face_detector"),
    **dict.fromkeys(("PassivePADDetector", "PADResult"), "passive_pad"),
    **dict.fromkeys(("ActiveLivenessDetector", "ChallengeState"), "active_liveness"),
    "ChallengeManager": "challenge_manager",
    **dict.fromkeys(("LivenessPipeline", "PipelineState", "PipelineStepResult"), "pipeline"),
}


def __getattr__(name):
    module = _EXPORT_MODULES.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module("." + module, __name__), name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))

__all__ = [
    "LivenessConfig",
    "WorkflowType",
    "WorkflowPolicy",
    "ChallengeType",
    "LivenessDecision",
    "FaceQualityAssessor",
    "DetectedFace",
    "QualityMetrics",
    "PassivePADDetector",
    "PADResult",
    "ActiveLivenessDetector",
    "ChallengeState",
    "ChallengeManager",
    "LivenessPipeline",
    "PipelineState",
    "PipelineStepResult"
]
