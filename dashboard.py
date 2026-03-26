import os
from datetime import datetime
from flask import Flask, render_template, jsonify
from utils.database import get_results, get_total_results, get_agent_statuses, get_insights

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/results")
def api_results():
    results = get_results(limit=50)
    return jsonify(results)

@app.route("/api/insights")
def api_insights():
    return jsonify(get_insights(limit=20))

@app.route("/api/stats")
def api_stats():
    statuses = get_agent_statuses()
    active = sum(1 for v in statuses.values() if v.get("status") == "active")
    return jsonify({
        "total_results": get_total_results(),
        "active_agents": active,
        "agents": statuses,
        "last_updated": datetime.now().strftime("%H:%M:%S")
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
