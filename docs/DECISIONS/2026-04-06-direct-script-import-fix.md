# Decision: fix config-runtime imports for direct script execution
Date: 2026-04-06

## Context
The config-first refactor was correct in principle, but the initial import path used:
- from scripts.lib.runtime_config import ...

This breaks when running scripts directly as:
- python3 scripts/<name>.py

because Python sets the script directory as sys.path[0].

## Decision
1. Keep the config-first runtime structure
2. Change direct-execution bridge scripts to import:
   - from lib.runtime_config import ...
3. Preserve compatibility with the current copy-paste execution workflow

## Outcome
The repository remains config-first while also staying compatible with direct script execution from the project root.
