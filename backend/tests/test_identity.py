"""Deleting the sign-in account in Cognito."""

from __future__ import annotations

from typing import Any

from letterlens.identity import CognitoDirectory


class _NotFoundError(Exception):
    pass


class _FakeCognito:
    class exceptions:  # noqa: N801 - mirrors the boto3 client attribute
        UserNotFoundException = _NotFoundError

    def __init__(self, missing: bool = False) -> None:
        self.calls: list[dict[str, Any]] = []
        self.missing = missing

    def admin_delete_user(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)
        if self.missing:
            raise _NotFoundError()


def test_deletes_the_user_by_subject_id() -> None:
    fake = _FakeCognito()
    CognitoDirectory("eu-central-1_pool", "eu-central-1", client=fake).delete_user("sub-1")
    assert fake.calls == [{"UserPoolId": "eu-central-1_pool", "Username": "sub-1"}]


def test_an_already_deleted_user_is_not_an_error() -> None:
    CognitoDirectory("p", "eu-central-1", client=_FakeCognito(missing=True)).delete_user("sub-1")
