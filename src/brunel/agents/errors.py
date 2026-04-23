class BrunelError(Exception):
    """Base error for Brunel runtime failures."""


class AgentNotFoundError(BrunelError):
    """Raised when a named agent cannot be resolved."""


class AgentSpecError(BrunelError):
    """Raised when an agent spec cannot be parsed or validated."""


class AgentRunError(BrunelError):
    """Raised when an agent run fails after validation."""
