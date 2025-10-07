from locust import HttpUser, task, between
import time, uuid, random, string

def uniq():
    t = int(time.time() * 1000)
    u = uuid.uuid4().hex[:6]
    uname = f"load_{t}_{u}"
    email = f"{uname}@load.com"
    pw = "hunter2!"
    return uname, email, pw

def big_text(n=10000):
    return "".join(random.choice(string.ascii_letters) for _ in range(n))

class MixedHeavyUser(HttpUser):
    wait_time = between(0.05, 0.15)

    @task(6)
    def health(self):
        self.client.get("/api/health", name="/api/health", timeout=5)

    @task(4)
    def signup_valid(self):
        uname, email, pw = uniq()
        self.client.post("/api/users", name="/api/users [valid]",
                         json={"username": uname, "email": email, "password_hash": pw}, timeout=10)

    @task(2)
    def signup_huge_payload(self):
        uname, email, pw = uniq()
        payload = {"username": uname, "email": email, "password_hash": pw, "bio": big_text(50_000)}
        self.client.post("/api/users", name="/api/users [huge]", json=payload, timeout=10)

    @task(2)
    def signup_wrong_content_type(self):
        uname, email, pw = uniq()
        body = f"username={uname}&email={email}&password_hash={pw}"
        self.client.post("/api/users", name="/api/users [wrong-ctype]",
                         data=body, headers={"Content-Type": "text/plain"}, timeout=10)

    @task(1)
    def email_case_conflict(self):
        uname, email, pw = uniq()
        self.client.post("/api/users", name="/api/users [base]",
                         json={"username": uname, "email": email, "password_hash": pw}, timeout=10)
        self.client.post("/api/users", name="/api/users [email-case]",
                         json={"username": f"{uname}_2", "email": email.upper(), "password_hash": pw}, timeout=10)



from locust import LoadTestShape

class StepLoadShape(LoadTestShape):
    """
    Ramps users in steps to observe thresholds.
    total_duration: 60s; users: 20 -> 50 -> 100 -> 0
    """
    stages = [
        {"duration": 10, "users": 50,  "spawn_rate": 20},
        {"duration": 30, "users": 100,  "spawn_rate": 25},
        {"duration": 50, "users": 200, "spawn_rate": 50},
        {"duration": 60, "users": 0,   "spawn_rate": 50},
    ]

    def tick(self):
        run_time = self.get_run_time()
        for s in self.stages:
            if run_time < s["duration"]:
                return (s["users"], s["spawn_rate"])
        return None

