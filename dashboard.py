import os
import sqlite3
import json
from datetime import datetime
from flask import Flask, render_template, jsonify, Response

app = Flask(__name__)

# Always use /data volume on Railway
DB_PATH = "/data/research.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def safe_query(query, params=()):
    try:
        conn = get_conn()
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"DB error: {e}")
        return []

def safe_count(query):
    try:
        conn = get_conn()
        count = conn.execute(query).fetchone()[0]
        conn.close()
        return count
    except:
        return 0

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/results")
def api_results():
    results = safe_query(
        "SELECT id, agent, topic, content, score, created_at FROM results ORDER BY created_at DESC LIMIT 50"
    )
    return jsonify(results)

@app.route("/api/insights")
def api_insights():
    insights = safe_query(
        "SELECT * FROM insights ORDER BY novelty_score DESC, created_at DESC LIMIT 20"
    )
    return jsonify(insights)

@app.route("/api/stats")
def api_stats():
    total = safe_count("SELECT COUNT(*) FROM results")
    agents_raw = safe_query("SELECT * FROM agent_status")
    agents = {r["agent"]: r for r in agents_raw}
    active = sum(1 for v in agents.values() if v.get("status") == "active")
    return jsonify({
        "total_results": total,
        "active_agents": active,
        "agents": agents,
        "last_updated": datetime.now().strftime("%H:%M:%S")
    })

@app.route("/api/export")
def api_export():
    results = safe_query("SELECT * FROM results ORDER BY created_at DESC")
    insights = safe_query("SELECT * FROM insights ORDER BY created_at DESC")
    export_data = {
        "exported_at": datetime.now().isoformat(),
        "total_results": len(results),
        "total_insights": len(insights),
        "results": results,
        "insights": insights
    }
    return Response(
        json.dumps(export_data, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=research_export.json"}
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, use_reloader=False)
