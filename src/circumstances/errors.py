class CircumstancesError(Exception):
    """Base error for actionable framework failures."""


class PackError(CircumstancesError):
    """Pack resolution, validation, or compatibility failure."""


class CapabilityError(CircumstancesError):
    """Selected subject cannot satisfy a pack or case requirement."""


class EvaluationError(CircumstancesError):
    """Evaluator could not produce a valid grade."""

