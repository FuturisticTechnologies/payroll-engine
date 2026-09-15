"""Sign-in behaviour."""
from __future__ import annotations

from fastapi.testclient import TestClient

ADMIN_PASSWORD = "Admin12345!"


def test_sign_in_does_not_depend_on_the_case_of_the_email(client: TestClient) -> None:
    """People do not type an email address the way it was stored.

    The seeded admin is admin@payrollfuturistic.co.uk; typing it with capitals
    is the same address and must not be told the credentials are wrong.
    """
    for typed in ("Admin@PayrollFuturistic.co.uk", "ADMIN@PAYROLLFUTURISTIC.CO.UK"):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": typed, "password": ADMIN_PASSWORD},
        )
        assert response.status_code == 200, (typed, response.text)


def test_wrong_password_is_refused_whatever_the_case_of_the_email(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "Admin@PayrollFuturistic.co.uk", "password": "Wrong12345!"},
    )
    assert response.status_code == 401
