"""Shared exceptions so CLI/API surfaces can translate failures consistently."""


class TienyError(Exception):
    """Base exception for expected Tieny failures."""


class ModelNotFoundError(TienyError):
    pass


class ModelNameConflictError(TienyError):
    pass


class RuntimeUnavailableError(TienyError):
    pass


class RuntimeStateError(TienyError):
    pass
