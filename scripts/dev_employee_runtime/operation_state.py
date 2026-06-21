from __future__ import annotations

from enum import Enum


class OperationState(str, Enum):
    PREPARED = "prepared"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    SUBMITTED = "submitted"
    CANCELLED = "cancelled"
