class RuntimeContractError(RuntimeError):
    """A validated runtime or configuration contract was violated."""


class AuthorizationError(RuntimeError):
    """An actor is not authorized for the requested project action."""


class ConflictError(RuntimeError):
    """A durable operation conflicts with existing state."""
