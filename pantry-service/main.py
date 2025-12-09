import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
CORS(app) 

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost/pantry_db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

ALLOWED_UNITS = {
    "lb", "oz", "g", "kg", 
    "fl oz", "ml", "l", "cup", "tbsp", "tsp", "gal",
    "unit", "qty", "can", "slice"
}

class Ingredient(db.Model):
    __tablename__ = "ingredients"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    expiration_date = db.Column(db.String(20), nullable=True) 
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "quantity": self.quantity,
            "unit": self.unit,
            "expiration_date": self.expiration_date
        }

with app.app_context():
    db.create_all()

def validate_item_data(data):
    if "name" not in data or "quantity" not in data or "unit" not in data:
        return "Missing name, quantity, or unit"

    if data["unit"].lower() not in ALLOWED_UNITS:
        return f"Invalid unit '{data['unit']}'. Allowed: {list(ALLOWED_UNITS)}"
        
    try:
        float(data["quantity"])
    except ValueError:
        return "Quantity must be a number"
    
    return None

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "pantry-service is running"})

@app.route("/pantry", methods=["GET"])
def get_pantry_items():
    ingredients = Ingredient.query.all()
    return jsonify([i.to_dict() for i in ingredients])

@app.route("/pantry", methods=["POST"])
def add_pantry_item():
    data = request.get_json()
    error_msg = validate_item_data(data)
    if error_msg:
        return jsonify({"error": error_msg}), 400

    new_item = Ingredient(
        name=data["name"],
        quantity=float(data["quantity"]),
        unit=data["unit"].lower(),
        expiration_date=data.get("expiration_date", None)
    )
    
    db.session.add(new_item)
    db.session.commit()
    return jsonify(new_item.to_dict()), 201

@app.route("/pantry/<int:id>", methods=["PUT"])
def update_pantry_item(id):
    item = Ingredient.query.get_or_404(id)
    data = request.get_json()

    if "name" in data:
        item.name = data["name"]
    
    if "quantity" in data:
        try:
            item.quantity = float(data["quantity"])
        except ValueError:
            return jsonify({"error": "Quantity must be a number"}), 400
            
    if "unit" in data:
        if data["unit"].lower() not in ALLOWED_UNITS:
            return jsonify({"error": "Invalid unit"}), 400
        item.unit = data["unit"].lower()
        
    if "expiration_date" in data:
        item.expiration_date = data["expiration_date"]

    db.session.commit()
    return jsonify(item.to_dict())

@app.route("/pantry/<int:id>", methods=["DELETE"])
def delete_pantry_item(id):
    item = Ingredient.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Item deleted"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)