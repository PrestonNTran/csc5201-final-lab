import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://user:password@db-postgres/pantry_db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class UsageStat(db.Model):
    __tablename__ = 'analytics'
    id = db.Column(db.Integer, primary_key=True)
    endpoint = db.Column(db.String(100), nullable=False)
    method = db.Column(db.String(10), nullable=False)
    
    count = db.Column(db.Integer, default=0)
    warning_count = db.Column(db.Integer, default=0) 
    error_count = db.Column(db.Integer, default=0)   
    
    total_latency = db.Column(db.Float, default=0.0)
    total_cpu = db.Column(db.Float, default=0.0)
    total_mem = db.Column(db.Float, default=0.0)

    def to_dict(self):
        avg_lat = (self.total_latency / self.count) if self.count > 0 else 0
        avg_cpu = (self.total_cpu / self.count) if self.count > 0 else 0
        avg_mem = (self.total_mem / self.count) if self.count > 0 else 0
        
        total_issues = self.warning_count + self.error_count
        success_rate = ((self.count - total_issues) / self.count) * 100 if self.count > 0 else 100

        return {
            "endpoint": self.endpoint,
            "method": self.method,
            "hits": self.count,
            "warnings": self.warning_count,
            "errors": self.error_count,
            "avg_latency": round(avg_lat, 2),
            "avg_cpu": round(avg_cpu, 1),
            "avg_mem": round(avg_mem, 1),
            "success_rate": round(success_rate, 1)
        }

with app.app_context():
    db.create_all()

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "Analytics Service Running"})

@app.route("/track", methods=["POST"])
def track_request():
    data = request.get_json()
    endpoint = data.get('endpoint')
    method = data.get('method')
    latency = data.get('latency', 0)
    status = data.get('status', 200)
    cpu = data.get('cpu', 0)
    mem = data.get('memory', 0)

    if not endpoint or not method:
        return jsonify({"error": "Missing data"}), 400

    stat = UsageStat.query.filter_by(endpoint=endpoint, method=method).first()
    
    if not stat:
        stat = UsageStat(
            endpoint=endpoint, 
            method=method, 
            count=0,
            warning_count=0,
            error_count=0,
            total_latency=0.0,
            total_cpu=0.0,
            total_mem=0.0
        )
        db.session.add(stat)
    
    stat.count += 1
    stat.total_latency += latency
    stat.total_cpu += cpu
    stat.total_mem += mem

    if 400 <= status < 500:
        stat.warning_count += 1
    elif status >= 500:
        stat.error_count += 1
    
    db.session.commit()
    return jsonify({"msg": "Logged"}), 200

@app.route("/stats", methods=["GET"])
def get_stats():
    stats = UsageStat.query.order_by(UsageStat.endpoint).all()
    return jsonify([s.to_dict() for s in stats])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)