import os
from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app) 

ALLOWED_UNITS = {
    "lb", "oz", "g", "kg", 
    "fl oz", "ml", "l", "cup", "tbsp", "tsp", "gal",
    "unit", "qty", "can", "slice"
}

@app.route("/", methods=["GET"])
def health_check():

@app.route("/plans", methods=["GET"])
def get_recipes():

@app.route("/plans", methods=["POST"])
def add_recipe():

@app.route("/plans/<id>", methods=["PUT"])
def update_recipe(id):

@app.route("/plans/<id>", methods=["DELETE"])
def delete_recipe(id):

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)