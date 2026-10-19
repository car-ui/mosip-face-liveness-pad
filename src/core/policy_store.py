"""Validated offline research policies. Model paths and API secrets are never stored."""
import copy
import json
import os
from pathlib import Path
import tempfile

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .config import LivenessConfig, WorkflowType, PADMode, ChallengeType


class PolicyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    liveness_enabled: bool | None = None
    guidance_messages: dict[str, str] | None = Field(default=None, max_length=16)
    workflow: WorkflowType = WorkflowType.RESIDENT_REGISTRATION
    passive_threshold: float | None = Field(default=None, ge=.46, le=.99)
    min_challenges: int | None = Field(default=None, ge=1, le=5)
    challenge_timeout: float | None = Field(default=None, ge=2, le=30)
    max_retries: int | None = Field(default=None, ge=0, le=5)
    pad_mode: PADMode | None = None
    active_liveness_enabled: bool | None = None
    require_active_challenges: bool | None = None
    supported_challenges: list[ChallengeType] | None = Field(default=None, min_length=1, max_length=6)

    @field_validator("guidance_messages")
    @classmethod
    def valid_guidance(cls, value):
        from .pipeline import PipelineState
        if value is not None and any(k not in {s.value for s in PipelineState} or len(v) > 300
                                     for k, v in value.items()):
            raise ValueError("Use pipeline state names and guidance of at most 300 characters")
        return value


def apply_update(current: LivenessConfig, update: PolicyUpdate):
    config = copy.deepcopy(current)
    for name in ("liveness_enabled", "guidance_messages", "pad_mode"):
        value = getattr(update, name)
        if value is not None:
            setattr(config, name, value)
    if update.supported_challenges is not None:
        config.supported_challenges = list(dict.fromkeys(update.supported_challenges))
    policy = config.get_policy(update.workflow)
    for name in ("passive_threshold", "min_challenges", "max_retries", "active_liveness_enabled",
                 "require_active_challenges"):
        value = getattr(update, name)
        if value is not None:
            setattr(policy, name, value)
    if update.challenge_timeout is not None:
        policy.challenge_timeout_seconds = update.challenge_timeout
    policy.max_challenges = max(policy.max_challenges, policy.min_challenges)
    if policy.require_active_challenges and not policy.active_liveness_enabled:
        raise ValueError("Required active challenges cannot be disabled")
    return config


class PolicyStore:
    def __init__(self, path):
        self.path = Path(path).expanduser().resolve()

    def load(self, base: LivenessConfig):
        if not self.path.exists():
            return copy.deepcopy(base)
        if self.path.stat().st_size > 1024 * 1024:
            raise ValueError("Policy file is too large")
        payload = json.loads(self.path.read_text(encoding="utf-8-sig"))
        if (not isinstance(payload, dict) or set(payload) != {"schemaVersion", "updates"}
                or payload["schemaVersion"] != 1 or not isinstance(payload["updates"], list)
                or len(payload["updates"]) != len(WorkflowType)):
            raise ValueError("Unsupported policy document")
        updates = [PolicyUpdate.model_validate(row) for row in payload["updates"]]
        if {row.workflow for row in updates} != set(WorkflowType):
            raise ValueError("Policy document must contain each workflow exactly once")
        config = copy.deepcopy(base)
        for update in updates:
            config = apply_update(config, update)
        # These values are global. Reject conflicting copies instead of relying
        # on document order to choose the last one.
        for name in ("liveness_enabled", "guidance_messages", "pad_mode", "supported_challenges"):
            values = [json.dumps(getattr(row, name), sort_keys=True) for row in updates]
            if len(set(values)) != 1:
                raise ValueError("Conflicting global policy values")
        return config

    def save(self, config: LivenessConfig):
        rows = []
        for workflow in WorkflowType:
            policy = config.get_policy(workflow)
            row = PolicyUpdate(
                workflow=workflow, passive_threshold=policy.passive_threshold,
                min_challenges=policy.min_challenges, challenge_timeout=policy.challenge_timeout_seconds,
                max_retries=policy.max_retries, active_liveness_enabled=policy.active_liveness_enabled,
                require_active_challenges=policy.require_active_challenges,
                liveness_enabled=config.liveness_enabled, guidance_messages=config.guidance_messages,
                pad_mode=config.pad_mode, supported_challenges=config.supported_challenges)
            apply_update(config, row)
            rows.append(row.model_dump(mode="json"))
        encoded = json.dumps({"schemaVersion": 1, "updates": rows}, indent=2) + "\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                             prefix=self.path.name + ".", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
