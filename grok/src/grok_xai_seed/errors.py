class GrokSeedError(Exception):
    """Base exception for grok-xai-seed."""


class PolicyDenied(GrokSeedError):
    """Task was denied by policy."""


class ExecutionError(GrokSeedError):
    """Grok execution failed before evidence could be captured."""


class VerificationError(GrokSeedError):
    """Receipt verification failed."""