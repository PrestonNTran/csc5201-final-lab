import os
import json
import threading
import requests
import re
import time
from datetime import datetime, timedelta
from dateutil import parser
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from kafka import KafkaConsumer

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://user:password@localhost/pantry_db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

ALLOWED_UNITS = {
    "lb", "oz", "g", "kg", 
    "fl oz", "ml", "l", "cup", "tbsp", "tsp", "gal",
    "unit", "qty", "can", "slice"
}

KEYWORDS_EARLY = ["marinate", "thaw", "soak", "overnight", "brine", "dry rub"]

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    due_date = db.Column(db.String(20), nullable=False) 
    status = db.Column(db.String(20), default="PENDING")
    recipe_name = db.Column(db.String(100))

    def to_dict(self):
        return {
            "id": self.id, 
            "description": self.description, 
            "due_date": self.due_date, 
            "status": self.status,
            "recipe_name": self.recipe_name
        }

with app.app_context():
    db.create_all()


def generate_prep_tasks(recipe_name, instructions, meal_date_str):
    tasks = []
    try:
        meal_date = parser.parse(meal_date_str)
    except:
        meal_date = datetime.now()

    tasks.append({
        "desc": f"Cook {recipe_name}",
        "date": meal_date_str
    })
    
    if not instructions:
        return tasks

    steps = re.split(r'[.\n\r,]+', instructions)
    
    for step in steps:
        clean_step = step.strip()
        if not clean_step: 
            continue
        
        lower_step = clean_step.lower()
        
        for word in KEYWORDS_EARLY:
            if word in lower_step:
                prep_date = meal_date - timedelta(days=1)
                
                if len(clean_step) > 60:
                    display_text = clean_step[:57] + "..."
                else:
                    display_text = clean_step

                tasks.append({
                    "desc": f"Prep ({recipe_name}): {display_text}",
                    "date": prep_date.strftime('%Y-%m-%d')
                })
                break 

    return tasks

def process_meal_plan(event):
    try:
        recipe_id = event['recipe_id']
        meal_date = event['date']
        
        url = f"http://recipe-service:5000/recipes/{recipe_id}"
        response = requests.get(url)
        
        if response.status_code == 200:
            target = response.json()
            new_tasks = generate_prep_tasks(target['name'], target.get('instructions', ''), meal_date)
            
            with app.app_context():
                for t in new_tasks:
                    task = Task(
                        description=t['desc'],
                        due_date=t['date'],
                        recipe_name=target['name']
                    )
                    db.session.add(task)
                db.session.commit()
                print(f"Generated {len(new_tasks)} tasks for {target['name']}", flush=True)
        else:
            print(f"Recipe {recipe_id} not found in Recipe Service", flush=True)
                
    except Exception as e:
        print(f"Error processing tasks: {e}", flush=True)

def listen_to_kafka():
    print("ToDo Service: Connecting to Kafka...", flush=True)
    while True:
        try:
            consumer = KafkaConsumer(
                'meal_events',
                bootstrap_servers='kafka:9092',
                auto_offset_reset='earliest',
                group_id='todo_group',
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            print("ToDo Service: Connected!", flush=True)
            
            for message in consumer:
                event = message.value
                if event.get('event') == 'MEAL_PLANNED':
                    process_meal_plan(event)
            break
        except Exception as e:
            print(f"Kafka not ready: {e}", flush=True)
            time.sleep(5)

threading.Thread(target=listen_to_kafka, daemon=True).start()

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "ToDo Service (Kafka) is running!"})

@app.route("/todo", methods=["GET"])
def get_tasks():
    tasks = Task.query.order_by(Task.due_date).all()
    return jsonify([t.to_dict() for t in tasks])

@app.route("/todo", methods=["POST"])
def add_task():
    """Manually add a task."""
    data = request.get_json()
    if not data or 'description' not in data or 'due_date' not in data:
        return jsonify({"error": "Missing description or due_date"}), 400

    new_task = Task(
        description=data['description'],
        due_date=data['due_date'],
        recipe_name=data.get('recipe_name', 'Manual'),
        status="PENDING"
    )
    db.session.add(new_task)
    db.session.commit()
    return jsonify(new_task.to_dict()), 201

@app.route("/todo/<int:id>", methods=["PUT"])
def update_task(id):
    task = Task.query.get_or_404(id)
    data = request.get_json()
    if 'status' in data:
        task.status = data['status']
    if 'description' in data:
        task.description = data['description']
    if 'due_date' in data:
        task.due_date = data['due_date']

    db.session.commit()
    return jsonify(task.to_dict())

@app.route("/todo/<int:id>", methods=["DELETE"])
def delete_task(id):
    task = Task.query.get_or_404(id)
    db.session.delete(task)
    db.session.commit()
    return jsonify({"message": "Task deleted"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)