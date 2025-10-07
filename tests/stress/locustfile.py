from locust import HttpUser, task, between
import time, uuid

def uniq():
    t = int(time.time() * 1000)
    u = uuid.uuid4().hex[:6]
    uname = f"load_{t}_{u}"
    email = f"{uname}@load.com"          # must end with .com (per your backend)
    pw = "hunter2!"                      # >= 6 chars
    return uname, email, pw

class QuickUser(HttpUser):
    """
    Lightweight mixed traffic:
    - /api/health (cheap read)
    - /api/users (valid creation)
    - /api/users (malformed / invalid)
    """
    wait_time = between(0.1, 0.5)

    @task(5)
    def health(self):
        self.client.get("/api/health", name="/api/health")

    @task(3)
    def create_user_valid(self):
        uname, email, pw = uniq()
        self.client.post("/api/users", name="/api/users [valid]",
                         json={"username": uname, "email": email, "password_hash": pw})

    @task(1)
    def create_user_duplicate_replay(self):
        # same payload twice -> should NOT create 2 users (expect 409 or 4xx on 2nd)
        uname, email, pw = uniq()
        payload = {"username": uname, "email": email, "password_hash": pw}
        self.client.post("/api/users", name="/api/users [dup-1]", json=payload)
        with self.client.post("/api/users", name="/api/users [dup-2]", json=payload, catch_response=True) as r:
            if r.status_code == 409:  # expected
                r.success()
            else:
                r.failure(f"Unexpected status {r.status_code}")


    @task(1)
    def create_user_bad_json(self):
        # Invalid JSON/body -> should 4xx, not 500
        self.client.post("/api/users", name="/api/users [bad-json]",
                         data='{"username": "oops"', headers={"Content-Type":"application/json"})
