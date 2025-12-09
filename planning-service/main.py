import os
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost/pantry_db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class MealPlan(db.Model):
    __tablename__ = "meal_plans"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=False)  
    recipe_id = db.Column(db.String(50), nullable=False)
    recipe_name = db.Column(db.String(100), nullable=False) 

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date,
            "recipe_id": self.recipe_id,
            "recipe_name": self.recipe_name
        }

with app.app_context():
    db.create_all()

def get_recipe_details(recipe_id):
    url = f"http://recipe-service:5000/recipes/{recipe_id}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return None
    except requests.exceptions.ConnectionError:
        return None

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "planning-service is running"})

@app.route("/plans", methods=["GET"])
def get_plans():
    plans = MealPlan.query.all()
    return jsonify([p.to_dict() for p in plans])

@app.route("/plans", methods=["POST"])
def create_plan():
    data = request.get_json()
    recipe_id = data.get("recipe_id")
    date = data.get("date")

    if not recipe_id or not date:
        return jsonify({"error": "Missing recipe_id or date"}), 400

    recipe = get_recipe_details(recipe_id)
    if not recipe:
        return jsonify({"error": "Recipe not found or Recipe Service is down"}), 404

    new_plan = MealPlan(
        date=date,
        recipe_id=recipe_id,
        recipe_name=recipe["name"]
    )
    db.session.add(new_plan)
    db.session.commit()
    return jsonify(new_plan.to_dict()), 201

@app.route("/plans/<int:id>", methods=["PUT"])
def update_plan(id):
    plan = MealPlan.query.get_or_404(id)
    data = request.get_json()

    if "date" in data:
        plan.date = data["date"]
    
    if "recipe_id" in data:
        recipe = get_recipe_details(data["recipe_id"])
        if not recipe:
             return jsonify({"error": "New recipe not found"}), 404

        plan.recipe_id = data["recipe_id"]
        plan.recipe_name = recipe["name"]

    db.session.commit()
    return jsonify(plan.to_dict())

@app.route("/plans/<int:id>", methods=["DELETE"])
def delete_plan(id):
    plan = MealPlan.query.get_or_404(id)
    db.session.delete(plan)
    db.session.commit()
    return jsonify({"message": "Plan deleted"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)