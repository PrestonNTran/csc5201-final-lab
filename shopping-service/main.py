import os
import json
import time
import threading
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from kafka import KafkaConsumer

app = Flask(__name__)
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost/pantry_db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class ShoppingItem(db.Model):
    __tablename__ = "shopping_list"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Float, default=1.0)
    unit = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default="PENDING")

    def to_dict(self):
        return {
            "id": self.id, 
            "name": self.name, 
            "quantity": self.quantity, 
            "unit": self.unit,
            "status": self.status
        }

with app.app_context():
    db.create_all()

def add_ingredients_to_list(recipe_id):
    try:
        print(f"🛒 Processing recipe ID: {recipe_id}...", flush=True)
        
        recipe_resp = requests.get(f"http://recipe-service:5000/recipes/{recipe_id}")
        if recipe_resp.status_code != 200: 
            print("Recipe service unavailable", flush=True)
            return
        recipe = recipe_resp.json()

        pantry_resp = requests.get("http://pantry-service:5000/pantry")
        if pantry_resp.status_code != 200: 
            print("Pantry service unavailable", flush=True)
            return
        inventory = { i["name"].lower(): float(i["quantity"]) for i in pantry_resp.json() }

        with app.app_context():
            print(f"🔍 Checking pantry for {recipe['name']}...", flush=True)
            for ing in recipe.get("ingredients", []):
                name = ing["item"].lower()
                needed = float(ing["amount"])
                owned = inventory.get(name, 0.0)
                
                if owned < needed:
                    buy_amount = needed - owned
                    new_item = ShoppingItem(name=ing["item"], quantity=buy_amount, unit=ing["unit"])
                    db.session.add(new_item)
                    print(f"Added {buy_amount} {ing['unit']} of {name}", flush=True)
                else:
                    print(f"Have enough {name}", flush=True)
            db.session.commit()
    except Exception as e:
        print(f"Error in logic: {e}", flush=True)

def listen_to_kafka():
    print("Shopping Service: Attempting to connect to Kafka...", flush=True)
    while True:
        try:
            consumer = KafkaConsumer(
                "meal_events",
                bootstrap_servers="kafka:9092",
                auto_offset_reset="earliest",
                group_id="shopping_group",
                value_deserializer=lambda x: json.loads(x.decode("utf-8"))
            )
            print("Shopping Service: CONNECTED to Kafka!", flush=True)
            for msg in consumer:
                event = msg.value
                print(f"📨 Received Kafka Event: {event}", flush=True)
                if event.get("event") == "MEAL_PLANNED":
                    add_ingredients_to_list(event["recipe_id"])
            break
        except Exception as e:
            print(f"⚠️ Kafka not ready. Error: {e}", flush=True)
            time.sleep(5)

threading.Thread(target=listen_to_kafka, daemon=True).start()

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "Shopping Service Running"})

@app.route("/shopping", methods=["GET"])
def get_list():
    items = ShoppingItem.query.all()
    items = sorted(items, key=lambda x: x.status, reverse=True)
    return jsonify([i.to_dict() for i in items])

@app.route("/shopping", methods=["POST"])
def add_item():
    data = request.get_json()
    new_item = ShoppingItem(
        name=data["name"], 
        quantity=float(data.get("quantity", 1)), 
        unit=data.get("unit", "unit")
    )
    db.session.add(new_item)
    db.session.commit()
    return jsonify(new_item.to_dict()), 201

@app.route("/shopping/<int:id>", methods=["PUT"])
def update_item(id):
    item = ShoppingItem.query.get_or_404(id)
    data = request.get_json()
    if "status" in data:
        new_status = data["status"]
        if new_status == "BOUGHT" and item.status != "BOUGHT":
            try:
                requests.post("http://pantry-service:5000/pantry", json={
                    "name": item.name,
                    "quantity": item.quantity,
                    "unit": item.unit
                })
                print(f"Auto-added {item.name} to Pantry", flush=True)
            except Exception as e:
                print(f"Pantry Sync Error: {e}", flush=True)
        item.status = new_status

    if "quantity" in data:
        item.quantity = float(data["quantity"])

    db.session.commit()
    return jsonify(item.to_dict())

@app.route("/shopping/<int:id>", methods=["DELETE"])
def delete_item(id):
    item = ShoppingItem.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"msg": "Deleted"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)