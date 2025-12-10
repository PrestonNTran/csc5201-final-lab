from locust import HttpUser, task, between
import random

class SimUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def view_dashboard(self):
        self.client.get("/")

    @task(3)
    def view_calendar_api(self):
        self.client.get("/api/calendar-events")

    @task(2)
    def view_recipes(self):
        self.client.get("/recipes")

    @task(2)
    def view_pantry(self):
        self.client.get("/pantry")

    @task(2)
    def view_shopping(self):
        self.client.get("/shopping")

    @task(2)
    def view_planner(self):
        self.client.get("/planner")

    @task(2)
    def view_tasks(self):
        self.client.get("/tasks")

    
    @task(1)
    def view_admin(self):
        self.client.get("/admin", auth=("username", "password"))

    @task(1)
    def add_shopping_item(self):
        self.client.post("/shopping/create", data={
            "name": "Load Test Item",
            "quantity": 1,
            "unit": "unit"
        })

    @task(1)
    def create_task(self):
        self.client.post("/tasks/create", data={
            "description": "Load Test Task",
            "due_date": "2025-12-31"
        })