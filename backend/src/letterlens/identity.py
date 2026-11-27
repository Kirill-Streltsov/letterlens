"""The sign-in directory (Amazon Cognito): remove the sign-in account when a person deletes their account.

The database keeps no email address. Cognito keeps the email address and the password hash.
Account deletion must remove both, otherwise "delete my account" would leave personal data behind.
"""

from __future__ import annotations

from typing import Any, Protocol


class IdentityDirectory(Protocol):
    def delete_user(self, sub: str) -> None: ...


class NoDirectory:
    """Local development: dev users exist only as a header."""

    def __init__(self) -> None:
        self.deleted: list[str] = []

    def delete_user(self, sub: str) -> None:
        self.deleted.append(sub)


class CognitoDirectory:
    def __init__(self, user_pool_id: str, region: str, client: Any | None = None) -> None:
        if client is None:
            import boto3

            client = boto3.client("cognito-idp", region_name=region)
        self._client = client
        self._pool = user_pool_id

    def delete_user(self, sub: str) -> None:
        # In a pool with email as the sign-in name, Cognito sets the user name to the subject id.
        try:
            self._client.admin_delete_user(UserPoolId=self._pool, Username=sub)
        except self._client.exceptions.UserNotFoundException:
            return  # Already deleted, for example by an earlier attempt.
