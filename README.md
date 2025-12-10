# csc5201-final-lab
This microservice-based application is designed to assist in meal planning. The application handles:
- Pantry inventory tracking - monitors ingredients, quantities, and expiration dates
- Recipe catalog - stores instructions and ingredient requirements
- Meal scheduling - schedules meals to a calendar and triggers grocery list and tasks
- Grocery list automation - populate a list when meals are planned
- Analytics - track requests to each endpoint and provide statistics

# Architecture
The application is composed of 7 Microservices orchestrated via Docker Compose:
- Frontend Service (Flask - Port 5000): The user interface and API gateway.
- Recipe Service (Flask + MongoDB - Port 5001): Manages recipe data.
- Pantry Service (Flask + PostgreSQL - Port 5002): Manages inventory.
- Planning Service (Flask + PostgreSQL + Kafka - Port 5003): Handles scheduling and triggers events.
- Shopping Service (Flask + PostgreSQL + Kafka - Port 5004): Consumes events to update shopping lists.
- Todo Service (Flask + PostgreSQL + Kafka - Port 5005): Consumes events to generate prep tasks.
- Analytics Service (Flask + PostgreSQL - Port 5006): Logs performance metrics.
Infrastructure:
- Message Broker: Apache Kafka + Zookeeper.
- Databases: PostgreSQL (Relational), MongoDB (Document).

# Installation
Prerequisites:
- Docker
- Docker Compose
- Locust (Optional)

Clone the repository:
```bash
- git clone https://github.com/PrestonNTran/csc5201-final-lab.git
```

Open the repository:
```bash
- cd csc5201-final-lab
```

Start the application:
```bash
- docker-compose up -d --build
```

Access the application:
- http://localhost:5000

Stop the application:
```bash
- docker-compose down
```

Load testing
Run locust
```bash
- locust
```

Access locust:
- http://localhost:8089
- Fill out users to send, users/second to add, website url

# API Documentation
API Documentation
Below are simple use cases for the core microservices. You can interact with these directly or via the Frontend.

1. Recipe Service
Manages the culinary data stored in MongoDB.
Endpoint: GET /recipes
Description: Retrieves a list of all available recipes.
Response Example:
```JSON
[
  {
    "id": "657a...",
    "name": "Spaghetti Carbonara",
    "ingredients": [{"item": "Pasta", "amount": 200, "unit": "g"}],
    "instructions": "Boil pasta..."
  }
]
```

2. Pantry Service
Manages current inventory levels in PostgreSQL.
Endpoint: POST /pantry
Description: Adds a new item to the pantry.
Request Example:
```JSON
{
  "name": "Chicken Breast",
  "quantity": 2.5,
  "unit": "lb",
  "expiration_date": "2025-12-31"
}
```

3. Planning Service (Event Trigger)
Creates a recipe to plan and triggers a Kafka event.
Endpoint: POST /plans
Description: Schedules a recipe for a specific date.
Side Effect: Fires a MEAL_PLANNED event to Kafka.
Request Example:
```JSON
{
  "date": "2025-10-15",
  "recipe_id": "657a..."
}
```

4. Shopping Service
Listens for planning events and checks the Pantry.
Endpoint: GET /shopping
Description: Returns the calculated shopping list. Items are added automatically if the Pantry Service reports insufficient quantity for a planned recipe.
Response Example:
```JSON
[
  {
    "id": 10,
    "name": "Eggs",
    "quantity": 6,
    "unit": "unit",
    "status": "PENDING"
  }
]
```

5. Analytics Service
Tracks system health and usage.
Endpoint: GET /stats
Description: Returns aggregated performance metrics for the Admin Dashboard.
Response Example:
```JSON
[
  {
    "endpoint": "/recipes",
    "hits": 150,
    "avg_latency": 35.5,
    "success_rate": 100.0
  }
]
```