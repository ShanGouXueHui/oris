from __future__ import annotations


def require_offline_mode(*, registered: bool, enabled: bool, runtime_dispatch: bool) -> None:
    if registered or enabled or runtime_dispatch:
        raise RuntimeError("offline foundation cannot register, enable or dispatch write actions")
