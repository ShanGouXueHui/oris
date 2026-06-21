#!/usr/bin/env python3
"""Compatibility entrypoint for the local-only ORIS Dev Employee Web console."""

from __future__ import annotations

from dev_employee_runtime.web_console_config import intake_request, json_response, write_audit_event
from dev_employee_runtime.web_console_page import page
from dev_employee_runtime.web_console_server import Handler, main

__all__ = [
    "Handler",
    "intake_request",
    "json_response",
    "main",
    "page",
    "write_audit_event",
]


if __name__ == "__main__":
    raise SystemExit(main())
