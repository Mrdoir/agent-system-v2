import os
import json
import psycopg2
import psycopg2.extras
from datetime import datetime
from flask import Flask, render_template, jsonify, Response, request

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")

def get_conn():
    return psycopg2.connect(DATABASE_URL)

def safe_query(query, params=()):
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"DB error: {e}")
        return []

def safe_count(query):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(query)
        count = cur.fetchone()[0]
        cur.close()
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
        json.dumps(export_data, indent=2, default=str),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=research_export.json"}
    )

@app.route("/api/import", methods=["GET", "POST"])
def api_import():
    if request.method == "GET":
        return """
        <html>
        <body style="font-family:monospace;background:#0a0a0a;color:#fff;padding:40px;">
            <h2>📦 Import Research Data</h2>
            <p>Upload your research_export.json file to restore all results.</p>
            <form method="post" enctype="multipart/form-data">
                <input type="file" name="file" accept=".json" style="color:#fff;margin:20px 0;display:block;">
                <button type="submit" style="background:#6366f1;color:#fff;border:none;padding:12px 24px;cursor:pointer;font-size:16px;">
                    Import All Results
                </button>
            </form>
        </body>
        </html>
        """
    file = request.files.get("file")
    if not file:
        return "No file uploaded", 400
    try:
        data = json.loads(file.read())
        results = data.get("results", [])
        insights = data.get("insights", [])
        conn = get_conn()
        cur = conn.cursor()

        # Make sure tables exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id SERIAL PRIMARY KEY,
                agent TEXT NOT NULL,
                topic TEXT NOT NULL,
                content TEXT NOT NULL,
                score INTEGER DEFAULT 0,
                tags TEXT DEFAULT '[]',
                created_at TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS insights (
                id SERIAL PRIMARY KEY,
                content TEXT NOT NULL,
                source_topics TEXT DEFAULT '[]',
                novelty_score INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()

        # Import results
        imported_results = 0
        for r in results:
            try:
                cur.execute(
                    "INSERT INTO results (agent, topic, content, score, tags, created_at) VALUES (%s,%s,%s,%s,%s,%s)",
                    (r.get("agent"), r.get("topic"), r.get("content"),
                     r.get("score", 0), r.get("tags", "[]"), r.get("created_at"))
                )
                imported_results += 1
            except:
                conn.rollback()

        # Import insights
        imported_insights = 0
        for i in insights:
            try:
                cur.execute(
                    "INSERT INTO insights (content, source_topics, novelty_score, created_at) VALUES (%s,%s,%s,%s)",
                    (i.get("content"), i.get("source_topics", "[]"),
                     i.get("novelty_score", 0), i.get("created_at"))
                )
                imported_insights += 1
            except:
                conn.rollback()

        conn.commit()
        cur.close()
        conn.close()
        return f"""
        <html>
        <body style="font-family:monospace;background:#0a0a0a;color:#fff;padding:40px;">
            <h2>✅ Import Complete!</h2>
            <p>📊 Results imported: {imported_results}</p>
            <p>🧠 Insights imported: {imported_insights}</p>
            <a href="/" style="color:#6366f1;">← Back to Dashboard</a>
        </body>
        </html>
        """
    except Exception as e:
        return f"❌ Import failed: {str(e)}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, use_reloader=False)
