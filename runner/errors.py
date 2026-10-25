from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    SUBMODULE_INCOMPLETE = "submodule_incomplete"
    PIPELINE_NOT_FOUND = "pipeline_not_found"
    VERSION_NOT_FOUND = "version_not_found"
    ENVIRONMENT = "environment"
    SAMPLESHEET_INVALID = "samplesheet_invalid"
    PARAMS_INVALID = "params_invalid"
    EXECUTION_FAILED = "execution_failed"
    HANDOFF_FAILED = "handoff_failed"
    ACCEPTANCE_REJECTED = "acceptance_rejected"


@dataclass
class NfclawError(Exception):
    code: ErrorCode
    message: str
    fix: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        lines = [f"[{self.code.value}] {self.message}"]
        for key, value in self.details.items():
            if isinstance(value, (list, tuple)):
                lines += [f"  - {item}" for item in value]
            else:
                lines.append(f"  {key}: {value}")
        if self.fix:
            lines.append(f"  fix: {self.fix}")
        return "\n".join(lines)
