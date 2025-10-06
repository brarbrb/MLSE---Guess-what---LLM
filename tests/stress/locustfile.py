from locust import HttpUser, task, between

class QuickUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(3)
    def health(self):
        self.client.get("/api/health")

    @task(1)
    def create_user(self):
        # Unique username per call to avoid collisions
        import time
        uname = f"load_{int(time.time()*1000)}"
        self.client.post("/api/users", json={"username": uname, "email": f"{uname}@e", "password_hash": "h"})
