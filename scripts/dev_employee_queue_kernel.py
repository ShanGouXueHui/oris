#!/usr/bin/env python3
"""Compatibility exports for the ORIS Dev Employee queue kernel.

The implementation is split under ``dev_employee_runtime`` so lifecycle storage,
cancellation, stale expiry, and idempotency helpers remain separately auditable.
Importing this module preserves the historical public surface.
"""

from __future__ import annotations

from dev_employee_runtime.queue_kernel import DEFAULT_KERNEL, QueueKernel
from dev_employee_runtime.queue_types import ACTIVE_SUFFIXES, TERMINAL_SUFFIXES, ClaimResult, LeaseMismatch, QueueKernelError, TaskConflict, TaskNotFound
from dev_employee_runtime.queue_utils import default_worker_id, generate_retry_task_id, request_fingerprint

__all__ = [
    "ACTIVE_SUFFIXES",
    "DEFAULT_KERNEL",
    "ClaimResult",
    "LeaseMismatch",
    "QueueKernel",
    "QueueKernelError",
    "TERMINAL_SUFFIXES",
    "TaskConflict",
    "TaskNotFound",
    "default_worker_id",
    "generate_retry_task_id",
    "request_fingerprint",
]
