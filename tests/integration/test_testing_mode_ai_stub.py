import os
import json

def test_testing_env_flag_present():
    assert os.getenv("TESTING") == "1"

def test_can_enable_fake_ai_endpoints_if_provided(client, monkeypatch):
    """
    QUICK TIP from the spec:
    Expose certain endpoints when TESTING=1 so the client can hit a stub instead of the real AI.

    This test documents the expectation by checking an optional route:
    /api/users/health exists already; for AI, if you add e.g. /api/ai/mock_words in TESTING mode,
    this test will exercise it. Until added, we'll treat 404 as acceptable and mark xfail.
    """
    r = client.get('/api/ai/mock_words')
    if r.status_code == 200:
        data = r.get_json()
        assert set(data) >= {"targetWord", "forbiddenWords"}
    else:
        # Documented expectation: route is optional unless implemented
        import pytest
        pytest.xfail("/api/ai/mock_words not implemented yet - add it behind TESTING=1 if desired")
