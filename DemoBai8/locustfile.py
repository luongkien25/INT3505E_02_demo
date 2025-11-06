from locust import HttpUser, task, between

class APIUser(HttpUser):
    """
    Load Test: Simulate multiple users accessing the API
    - GET /users: retrieve user list
    - POST /users: create new user
    """
    wait_time = between(1, 3)  # wait 1-3 seconds between requests
    
    @task(3)  # weight: 3x more GET than POST
    def get_users(self):
        """Simulate user retrieving the user list"""
        self.client.get("/users")
    
    @task(1)
    def create_user(self):
        """Simulate user creating a new user"""
        payload = {
            "name": f"LoadTest User {self.environment.stats.num_requests}",
            "email": f"loadtest{self.environment.stats.num_requests}@example.com"
        }
        self.client.post("/users", json=payload)


# Run instructions:
# 1. Start Flask app: python app.py
# 2. Start Locust: locust -f locustfile.py --host=http://127.0.0.1:5000
# 3. Open browser: http://localhost:8089
# 4. Configure: Number of users (e.g., 10-50), Spawn rate (e.g., 5/sec)
# 5. Start test and watch real-time metrics!
