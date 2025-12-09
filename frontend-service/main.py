from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import requests

app = Flask(__name__)
app.secret_key = 'supersecretkey' 

RECIPE_API = "http://recipe-service:5000/recipes"
PANTRY_API = "http://pantry-service:5000/pantry"
PLANNING_API = "http://planning-service:5000/plans"

ALLOWED_UNITS = sorted(list({
    "lb", "oz", "g", "kg", 
    "fl oz", "ml", "l", "cup", "tbsp", "tsp", "gal",
    "unit", "qty", "can", "slice"
}))

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/recipes')
def list_recipes():
    try:
        recipes = requests.get(RECIPE_API).json()
    except:
        recipes = []
        flash("Error: Recipe Service Unreachable")
    return render_template('recipes.html', recipes=recipes, units=ALLOWED_UNITS)

@app.route('/recipes/create', methods=['POST'])
def create_recipe():
    name = request.form.get('name')
    instructions = request.form.get('instructions')
    
    ingredients = []
    items = request.form.getlist('items[]')
    amounts = request.form.getlist('amounts[]')
    units = request.form.getlist('units[]')
    
    for i in range(len(items)):
        if items[i]: 
            ingredients.append({
                "item": items[i],
                "amount": float(amounts[i]),
                "unit": units[i]
            })

    payload = {"name": name, "instructions": instructions, "ingredients": ingredients}
    requests.post(RECIPE_API, json=payload)
    return redirect(url_for('list_recipes'))

@app.route('/recipes/edit/<id>')
def edit_recipe(id):
    try:
        response = requests.get(f"{RECIPE_API}/{id}")
        if response.status_code == 200:
            recipe = response.json()
            return render_template('edit_recipe.html', recipe=recipe, units=ALLOWED_UNITS)
        else:
            flash("Recipe not found.")
            return redirect(url_for('list_recipes'))
    except Exception as e:
        flash(f"Error fetching recipe: {e}")
        return redirect(url_for('list_recipes'))

@app.route('/recipes/update/<id>', methods=['POST'])
def update_recipe(id):
    name = request.form.get('name')
    instructions = request.form.get('instructions')
    
    ingredients = []
    items = request.form.getlist('items[]')
    amounts = request.form.getlist('amounts[]')
    units = request.form.getlist('units[]')
    
    for i in range(len(items)):
        if items[i]: 
            ingredients.append({
                "item": items[i],
                "amount": float(amounts[i]),
                "unit": units[i]
            })

    payload = {"name": name, "instructions": instructions, "ingredients": ingredients}
    
    try:
        requests.put(f"{RECIPE_API}/{id}", json=payload)
        flash("Recipe updated successfully!")
    except Exception as e:
        flash(f"Error updating recipe: {e}")

    return redirect(url_for('list_recipes'))

@app.route('/recipes/delete/<id>', methods=['POST'])
def delete_recipe(id):
    try:
        requests.delete(f"{RECIPE_API}/{id}")
        flash("Recipe deleted.")
    except Exception as e:
        flash(f"Error deleting recipe: {e}")
    return redirect(url_for('list_recipes'))

@app.route('/pantry')
def list_pantry():
    try:
        pantry = requests.get(PANTRY_API).json()
        pantry = sorted(pantry, key=lambda x: x['name'])
    except:
        pantry = []
    return render_template('pantry.html', pantry=pantry, units=ALLOWED_UNITS)

@app.route('/pantry/create', methods=['POST'])
def add_pantry_item():
    payload = {
        "name": request.form.get('name'),
        "quantity": float(request.form.get('quantity')),
        "unit": request.form.get('unit'),
        "expiration_date": request.form.get('expiration_date')
    }
    try:
        requests.post(PANTRY_API, json=payload)
    except Exception as e:
        flash(f"Error adding item: {e}")
        
    return redirect(url_for('list_pantry'))

@app.route('/pantry/update/<id>', methods=['POST'])
def update_pantry_item(id):
    new_quantity = request.form.get('quantity')
    try:
        url = f"{PANTRY_API}/{id}"
        requests.put(url, json={"quantity": float(new_quantity)})
        flash("Quantity updated!")
    except Exception as e:
        flash(f"Error updating item: {e}")
        
    return redirect(url_for('list_pantry'))

@app.route('/pantry/delete/<id>', methods=['POST'])
def delete_pantry_item(id):
    try:
        url = f"{PANTRY_API}/{id}"
        requests.delete(url)
        flash("Item removed.")
    except Exception as e:
        flash(f"Error removing item: {e}")
    return redirect(url_for('list_pantry'))

@app.route('/planner')
def planner():
    try:
        plans = requests.get(PLANNING_API).json()
        recipes = requests.get(RECIPE_API).json()
    except:
        plans = []
        recipes = []
    return render_template('planner.html', plans=plans, recipes=recipes)

@app.route('/planner/create', methods=['POST'])
def create_plan():
    payload = {
        "date": request.form.get('date'),
        "recipe_id": request.form.get('recipe_id')
    }
    requests.post(PLANNING_API, json=payload)
    flash("Meal Planned! Shopping List updating in background...")
    return redirect(url_for('planner'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)