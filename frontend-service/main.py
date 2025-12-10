from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response, g
from functools import wraps
import psutil
import time
import requests
import threading


app = Flask(__name__)
app.secret_key = 'supersecretkey' 

RECIPE_API = "http://recipe-service:5000/recipes"
PANTRY_API = "http://pantry-service:5000/pantry"
PLANNING_API = "http://planning-service:5000/plans"
SHOPPING_API = "http://shopping-service:5000/shopping"
TODO_API = "http://todo-service:5000/todo"
ANALYTICS_API = "http://analytics-service:5000"


ALLOWED_UNITS = sorted(list({
    "lb", "oz", "g", "kg", 
    "fl oz", "ml", "l", "cup", "tbsp", "tsp", "gal",
    "unit", "qty", "can", "slice"
}))

def check_auth(username, password):
    return username == 'username' and password == 'password'

def authenticate():
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.before_request
def start_metrics():
    g.start_time = time.time()

@app.after_request
def track_analytics(response):
    if request.path.startswith('/static') or request.path.startswith('/api'):
        return response

    duration = (time.time() - g.start_time) * 1000
    cpu_usage = psutil.cpu_percent(interval=None) 
    mem_usage = psutil.virtual_memory().percent

    status_code = response.status_code

    def send_data(path, method, lat, status, cpu, mem):
        try:
            requests.post(f"{ANALYTICS_API}/track", json={
                "endpoint": path,
                "method": method,
                "latency": lat,
                "status": status,
                "cpu": cpu,
                "memory": mem
            })
        except:
            pass

    threading.Thread(target=send_data, args=(
        request.path, request.method, duration, status_code, cpu_usage, mem_usage
    )).start()
    
    return response

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

@app.route('/shopping')
def shopping_list():
    try:
        response = requests.get(SHOPPING_API)
        items = response.json() if response.status_code == 200 else []
    except:
        items = []
        flash("Error connecting to Shopping Service")
    return render_template('shopping.html', items=items, units=ALLOWED_UNITS)

@app.route('/shopping/create', methods=['POST'])
def add_shopping_item():
    payload = {
        "name": request.form.get('name'),
        "quantity": float(request.form.get('quantity')),
        "unit": request.form.get('unit')
    }
    try:
        requests.post(SHOPPING_API, json=payload)
    except Exception as e:
        flash(f"Error adding item: {e}")
    return redirect(url_for('shopping_list'))

@app.route('/shopping/buy/<id>', methods=['POST'])
def mark_bought(id):
    try:
        requests.put(f"{SHOPPING_API}/{id}", json={"status": "BOUGHT"})
        flash("Item marked as bought & added to Pantry!")
    except Exception as e:
        flash(f"Error updating item: {e}")
    return redirect(url_for('shopping_list'))

@app.route('/shopping/delete/<id>', methods=['POST'])
def delete_shopping_item(id):
    try:
        requests.delete(f"{SHOPPING_API}/{id}")
        flash("Item removed from list.")
    except Exception as e:
        flash(f"Error deleting item: {e}")
    return redirect(url_for('shopping_list'))

@app.route('/tasks')
def list_tasks():
    try:
        response = requests.get(TODO_API)
        tasks = response.json() if response.status_code == 200 else []
        tasks = sorted(tasks, key=lambda x: x['status'])
    except:
        tasks = []
        flash("Error connecting to ToDo Service")
    return render_template('tasks.html', tasks=tasks)

@app.route('/tasks/create', methods=['POST'])
def create_manual_task():
    payload = {
        "description": request.form.get('description'),
        "due_date": request.form.get('due_date'),
        "recipe_name": "Manual"
    }
    try:
        requests.post(TODO_API, json=payload)
    except Exception as e:
        flash(f"Error creating task: {e}")
    return redirect(url_for('list_tasks'))

@app.route('/tasks/complete/<id>', methods=['POST'])
def complete_task(id):
    try:
        if request.form.get('_method') == 'DELETE':
             requests.delete(f"{TODO_API}/{id}")
        else:
             requests.put(f"{TODO_API}/{id}", json={"status": "DONE"})
    except Exception as e:
        flash(f"Error updating task: {e}")
    return redirect(url_for('list_tasks'))

@app.route('/api/calendar-events')
def calendar_events():
    events = []
    try:
        plans = requests.get(PLANNING_API).json()
        for p in plans:
            events.append({
                "title": f"🍽️ {p['recipe_name']}",
                "start": p['date'],
                "color": "#3498db", 
                "url": "/planner"
            })
    except: pass

    try:
        tasks = requests.get(TODO_API).json()
        for t in tasks:
            if t['description'].startswith("Cook "):
                continue

            color = "#27ae60" if t['status'] == 'DONE' else "#e67e22"
            prefix = "✅" if t['status'] == 'DONE' else "⬜"
            
            events.append({
                "title": f"{prefix} {t['description']}",
                "start": t['due_date'],
                "color": color,
                "url": "/tasks"
            })
    except: pass

    return jsonify(events)

@app.route('/admin')
@requires_auth
def admin_stats():
    try:
        response = requests.get(f"{ANALYTICS_API}/stats")
        stats = response.json() if response.status_code == 200 else []
    except:
        stats = []
        flash("Error connecting to Analytics Service")
    return render_template('admin.html', stats=stats)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)