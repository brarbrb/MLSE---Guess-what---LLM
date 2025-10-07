import os
import pytest

def test_testing_env_flag_present():
    assert os.getenv("TESTING") == "1"

def test_can_enable_fake_ai_endpoints_if_provided(client):
    r = client.get('/api/ai/mock_words')
    if r.status_code == 404:
        pytest.skip("No TESTING mock AI endpoint present; skipping by design.")
    assert r.status_code == 200
    data = r.get_json()
    assert set(data) >= {"targetWord", "forbiddenWords"}
