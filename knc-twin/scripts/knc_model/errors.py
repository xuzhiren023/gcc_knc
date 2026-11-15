"""Explicit result statuses. Every failure mode has a status string that ends up in result.json."""


class TwinError(Exception):
    status = "error"
    exit_code = 1

    def __init__(self, message, details=None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self):
        return {"status": self.status, "message": self.message, "details": self.details}


class InvalidInput(TwinError):
    status = "invalid_input"
    exit_code = 2


class Unsupported(TwinError):
    status = "unsupported"
    exit_code = 3


class MissingParameter(TwinError):
    status = "missing_parameter"
    exit_code = 4


class BudgetExhausted(TwinError):
    status = "budget_exhausted"
    exit_code = 5

    def __init__(self, message, details=None, partial=None):
        super().__init__(message, details)
        self.partial = partial or {}


class FunctionalMismatch(TwinError):
    status = "functional_mismatch"
    exit_code = 6


class NeedsParameters(TwinError):
    status = "needs_parameters"
    exit_code = 7


STATUS_EXIT_CODES = {
    "ok": 0,
    "invalid_input": 2,
    "unsupported": 3,
    "missing_parameter": 4,
    "budget_exhausted": 5,
    "functional_mismatch": 6,
    "needs_parameters": 7,
    "incompatible": 8,
    "error": 1,
}
