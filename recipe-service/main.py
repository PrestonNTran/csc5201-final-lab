import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId

app = Flask(__name__)
CORS(app) 
client = MongoClient("mongodb://db-mongo:27017/")
db = client.recipe_db
recipes_collection = db.recipes

ALLOWED_UNITS = {
    "lb", "oz", "g", "kg", 
    "fl oz", "ml", "l", "cup", "tbsp", "tsp", "gal",
    "unit", "qty", "can", "slice"
}

def fix_id(doc):
    doc["id"] = str(doc.pop("_id"))
    return doc

def validate_recipe_data(data):
    if not data or "name" not in data or "ingredients" not in data:
        return None, (jsonify({"error": "Missing name or ingredients"}), 400)

    ingredients = data["ingredients"]
    if not isinstance(ingredients, list):
        return None, (jsonify({"error": "Ingredients must be a list"}), 400)

    cleaned_ingredients = []
    for i, ing in enumerate(ingredients):
        if not isinstance(ing, dict):
            return None, (jsonify({"error": f"Item at index {i} must be an object"}), 400)

        if "item" not in ing or "amount" not in ing or "unit" not in ing:
            return None, (jsonify({"error": f"Item at index {i} is missing 'item', 'amount', or 'unit'"}), 400)

        unit = ing["unit"].lower()
        if unit not in ALLOWED_UNITS:
            return None, (jsonify({
                "error": f"Invalid unit '{unit}' for '{ing['item']}'. Allowed: {list(ALLOWED_UNITS)}"
            }), 400)

        try:
            amount = float(ing["amount"])
        except ValueError:
             return None, (jsonify({"error": f"Amount for '{ing['item']}' must be a number"}), 400)
        
        cleaned_ingredients.append({
            "item": ing["item"],
            "amount": amount,
            "unit": unit
        })

    return {
        "name": data["name"],
        "instructions": data.get("instructions", ""),
        "ingredients": cleaned_ingredients
    }, None


@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "recipe-service is running"})

@app.route("/recipes", methods=["GET"])
def get_recipes():
    cursor = recipes_collection.find({})
    output = []
    for doc in cursor:
        output.append(fix_id(doc))

    return jsonify(output)

@app.route("/recipes/<id>", methods=["GET"])
def get_recipe(id):
    try:
        object_id = ObjectId(id)
    except:
        return jsonify({"error": "Invalid ID format"}), 400

    doc = recipes_collection.find_one({"_id": object_id})
    if not doc:
        return jsonify({"error": "Recipe not found"}), 404
    
    return jsonify(fix_id(doc))

@app.route("/recipes", methods=["POST"])
def add_recipe():
    data = request.get_json()
    clean_data, error = validate_recipe_data(data)
    if error:
        return error

    result = recipes_collection.insert_one(clean_data)
    new_doc = recipes_collection.find_one({"_id": result.inserted_id})
    return jsonify(fix_id(new_doc)), 201

@app.route("/recipes/<id>", methods=["PUT"])
def update_recipe(id):
    data = request.get_json()
    clean_data, error = validate_recipe_data(data)
    if error:
        return error

    try:
        object_id = ObjectId(id)
    except:
        return jsonify({"error": "Invalid ID format"}), 400

    result = recipes_collection.update_one(
        {"_id": object_id},
        {"$set": clean_data}
    )

    if result.matched_count == 0:
        return jsonify({"error": "Recipe not found"}), 404

    updated_doc = recipes_collection.find_one({"_id": object_id})
    return jsonify(fix_id(updated_doc))

@app.route("/recipes/<id>", methods=["DELETE"])
def delete_recipe(id):
    try:
        object_id = ObjectId(id)
    except:
        return jsonify({"error": "Invalid ID format"}), 400

    result = recipes_collection.delete_one({"_id": object_id})
    if result.deleted_count == 0:
        return jsonify({"error": "Recipe not found"}), 404

    return jsonify({"message": "Recipe deleted"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)