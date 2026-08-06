"""API errors with stable machine-readable codes."""

from __future__ import annotations


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def not_found(what: str = "resource") -> ApiError:
    # Same answer for "does not exist" and "not yours": RLS hides foreign rows.
    return ApiError(404, "not_found", f"{what} not found")


def forbidden(message: str = "not allowed") -> ApiError:
    return ApiError(403, "forbidden", message)


def bad_request(code: str, message: str) -> ApiError:
    return ApiError(400, code, message)
