# Dev Employee Runtime Authorities

This package owns reusable commercial runtime primitives: clock, validated settings,
project-registry resolution, environment files, atomic JSON storage, bounded HTTP
response parsing, identifier validation and filesystem locking.

Runtime entrypoints must import these authorities. They must not copy equivalent
helpers or embed environment-specific paths, endpoints, branches, projects,
providers or models in shared source.
