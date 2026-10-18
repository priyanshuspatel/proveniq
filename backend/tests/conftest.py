import pytest


# This value exists only in the test process; runtime configuration has no source default.
TEST_ACCESS_TOKEN = "test-only-proveniq-access-token"


@pytest.fixture(autouse=True)
def test_access_token(monkeypatch):
    monkeypatch.setenv("PROVENIQ_ACCESS_TOKEN", TEST_ACCESS_TOKEN)
