"""
DASHBOARD v3 — Flask API with analytics and search
Improvements:
- Full-text search endpoint
- Analytics endpoints
- Topic saturation info
- Agent performance stats
- Better error handling
"""

import os
import json
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, Response, request

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")


def get_conn():
    """Get database connection."""
    return psycopg2.connect(DATABASE_URL)


def safe_query(query, params=()):
    """Execute query with error handling."""
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


def safe_count(query, params=()):
    """Execute count query."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(query, params)
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return count
    except Exception as e:
        print(f"DB count error: {e}")
        return 0


def safe_execute(query, params=()):
    """Execute a write query."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"DB execute error: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════
# MAIN ROUTES
# ═══════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    """Serve the dashboard."""
    return render_template("index.html")


# ═══════════════════════════════════════════════════════════════════
# CORE API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/results")
def api_results():
    """Get recent results with optional filtering."""
    limit = request.args.get("limit", 50, type=int)
    agent = request.args.get("agent", None)
    min_score = request.args.get("min_score", None, type=int)
    
    query = "SELECT id, agent, topic, content, score, created_at FROM results WHERE 1=1"
    params = []
    
    if agent:
        query += " AND agent = %s"
        params.append(agent)
    
    if min_score:
        query += " AND score >= %s"
        params.append(min_score)
    
    query += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)
    
    results = safe_query(query, params)
    return jsonify(results)


@app.route("/api/insights")
def api_insights():
    """Get insights with optional novelty filter."""
    limit = request.args.get("limit", 20, type=int)
    min_novelty = request.args.get("min_novelty", None, type=int)
    
    if min_novelty:
        insights = safe_query(
            """SELECT * FROM insights 
               WHERE novelty_score >= %s
               ORDER BY novelty_score DESC, created_at DESC 
               LIMIT %s""",
            (min_novelty, limit)
        )
    else:
        insights = safe_query(
            "SELECT * FROM insights ORDER BY novelty_score DESC, created_at DESC LIMIT %s",
            (limit,)
        )
    
    return jsonify(insights)


@app.route("/api/stats")
def api_stats():
    """Get system statistics."""
    total = safe_count("SELECT COUNT(*) FROM results")
    agents_raw = safe_query("SELECT * FROM agent_status")
    agents = {r["agent"]: r for r in agents_raw}
    active = sum(1 for v in agents.values() if v.get("status") == "active")
    
    # Additional stats
    high_quality = safe_count("SELECT COUNT(*) FROM results WHERE score >= 7")
    today = datetime.now().date().isoformat()
    try:
        today_count = safe_count(
            "SELECT COUNT(*) FROM results WHERE created_at LIKE %s",
            (today + "%",)
        )
    except Exception:
        today_count = 0
    
    return jsonify({
        "total_results": total,
        "active_agents": active,
        "agents": agents,
        "high_quality_results": high_quality,
        "results_today": today_count,
        "last_updated": datetime.now().strftime("%H:%M:%S")
    })


# ═══════════════════════════════════════════════════════════════════
# SEARCH ENDPOINT
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/search")
def api_search():
    """Full-text search across results."""
    q = request.args.get("q", "").strip()
    limit = request.args.get("limit", 30, type=int)
    
    if not q:
        return jsonify([])
    
    results = safe_query("""
        SELECT id, agent, topic, content, score, created_at
        FROM results
        WHERE content ILIKE %s OR topic ILIKE %s
        ORDER BY score DESC, created_at DESC
        LIMIT %s
    """, (f"%{q}%", f"%{q}%", limit))
    
    return jsonify(results)


# ═══════════════════════════════════════════════════════════════════
# ANALYTICS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/analytics/summary")
def api_analytics_summary():
    """Get analytics summary."""
    # Overall stats
    overall = safe_query("""
        SELECT 
            COUNT(*) as total_results,
            AVG(score) as avg_score,
            COUNT(CASE WHEN score >= 7 THEN 1 END) as high_quality,
            COUNT(DISTINCT topic) as unique_topics,
            COUNT(DISTINCT agent) as active_agents
        FROM results
    """)
    
    # Per-agent stats
    agents = safe_query("""
        SELECT agent, COUNT(*) as count, AVG(score) as avg_score
        FROM results
        GROUP BY agent
    """)
    
    # Last 24h
    last_24h = safe_count("""
        SELECT COUNT(*) FROM results
        WHERE created_at > %s
    """, ((datetime.now() - timedelta(hours=24)).isoformat(),))
    
    # Top topics
    top_topics = safe_query("""
        SELECT topic, COUNT(*) as count, AVG(score) as avg_score
        FROM results
        GROUP BY topic
        ORDER BY count DESC
        LIMIT 10
    """)
    
    return jsonify({
        "overall": overall[0] if overall else {},
        "agents": {a["agent"]: a for a in agents},
        "last_24h": last_24h,
        "top_topics": top_topics
    })


@app.route("/api/analytics/scores")
def api_analytics_scores():
    """Get score trends over time."""
    days = request.args.get("days", 30, type=int)
    
    trends = safe_query("""
        SELECT 
            DATE(created_at) as date,
            agent,
            AVG(score) as avg_score,
            COUNT(*) as count
        FROM results
        WHERE created_at > %s
        GROUP BY DATE(created_at), agent
        ORDER BY date
    """, ((datetime.now() - timedelta(days=days)).isoformat(),))
    
    return jsonify(trends)


@app.route("/api/analytics/topics")
def api_analytics_topics():
    """Get topic analytics."""
    topics = safe_query("""
        SELECT 
            topic, 
            COUNT(*) as research_count, 
            AVG(score) as avg_score,
            MAX(created_at) as last_researched
        FROM results 
        GROUP BY topic 
        ORDER BY research_count DESC 
        LIMIT 50
    """)
    
    # Add saturation status
    for t in topics:
        t["is_saturated"] = t["research_count"] >= 5 and (t["avg_score"] or 0) < 6
    
    return jsonify(topics)


@app.route("/api/analytics/agents")
def api_analytics_agents():
    """Get detailed agent analytics."""
    agents = safe_query("""
        SELECT 
            agent,
            COUNT(*) as total_results,
            AVG(score) as avg_score,
            MAX(score) as best_score,
            MIN(created_at) as first_result,
            MAX(created_at) as last_result,
            COUNT(CASE WHEN score >= 7 THEN 1 END) as high_quality_count
        FROM results
        GROUP BY agent
    """)
    
    # Add status info
    statuses = safe_query("SELECT * FROM agent_status")
    status_map = {s["agent"]: s for s in statuses}
    
    for a in agents:
        status = status_map.get(a["agent"], {})
        a["status"] = status.get("status", "unknown")
        a["tasks_completed"] = status.get("tasks_completed", 0)
        a["rate_limit_until"] = status.get("rate_limit_until")
        a["current_provider"] = status.get("current_provider")
    
    return jsonify(agents)


# ═══════════════════════════════════════════════════════════════════
# FEEDBACK ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/feedback/<agent>")
def api_agent_feedback(agent):
    """Get critic feedback for an agent."""
    limit = request.args.get("limit", 10, type=int)
    
    feedback = safe_query("""
        SELECT * FROM critic_feedback
        WHERE agent = %s
        ORDER BY created_at DESC
        LIMIT %s
    """, (agent, limit))
    
    # Get average score
    avg = safe_query(
        "SELECT AVG(score) as avg_score FROM critic_feedback WHERE agent = %s",
        (agent,)
    )
    
    return jsonify({
        "feedback": feedback,
        "avg_score": round(avg[0]["avg_score"] or 0, 1) if avg else 0
    })


# ═══════════════════════════════════════════════════════════════════
# EXPORT/IMPORT
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/export")
def api_export():
    """Export all data as JSON."""
    results = safe_query("SELECT * FROM results ORDER BY created_at DESC")
    insights = safe_query("SELECT * FROM insights ORDER BY created_at DESC")
    feedback = safe_query("SELECT * FROM critic_feedback ORDER BY created_at DESC")
    
    export_data = {
        "exported_at": datetime.now().isoformat(),
        "total_results": len(results),
        "total_insights": len(insights),
        "results": results,
        "insights": insights,
        "critic_feedback": feedback
    }
    
    return Response(
        json.dumps(export_data, indent=2, default=str),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=research_export.json"}
    )


@app.route("/api/import", methods=["GET", "POST"])
def api_import():
    """Import data from JSON file."""
    if request.method == "GET":
        return """
        <html>
        <body style="font-family:monospace;background:#0a0a0a;color:#fff;padding:40px;">
            <h2>📦 Import Research Data</h2>
            <p>Upload your research_export.json file to restore all results.</p>
            <form method="post" enctype="multipart/form-data">
                <input type="file" name="file" accept=".json" style="color:#fff;margin:20px 0;display:block;">
                <button type="submit" style="background:#7c6fcd;color:#fff;border:none;padding:12px 24px;cursor:pointer;font-size:16px;border-radius:8px;">
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
        
        # Ensure tables exist
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
                    """INSERT INTO results (agent, topic, content, score, tags, created_at) 
                       VALUES (%s,%s,%s,%s,%s,%s)""",
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
                    """INSERT INTO insights (content, source_topics, novelty_score, created_at) 
                       VALUES (%s,%s,%s,%s)""",
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
            <h2>✅ Import Complete</h2>
            <p>Imported {imported_results} results and {imported_insights} insights.</p>
            <a href="/" style="color:#7c6fcd;">← Back to Dashboard</a>
        </body>
        </html>
        """
        
    except Exception as e:
        return f"Import error: {e}", 500


# ═══════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════

@app.route("/health")
def health():
    """Health check endpoint."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return jsonify({"status": "healthy", "database": "connected"})
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


@app.route("/api/debug_db")
def api_debug_db():
    """Deep diagnostics endpoint for database verification."""
    debug_info = {}
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        # 1. Check connection params
        dsn = conn.get_dsn_parameters()
        debug_info["connection"] = {
            "host": dsn.get("host"),
            "port": dsn.get("port"),
            "dbname": dsn.get("dbname"),
            "user": dsn.get("user")
        }
        
        # 2. Check existing tables
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = [r[0] for r in cur.fetchall()]
        debug_info["tables_found"] = tables
        
        # 3. Check counts
        counts = {}
        for t in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                counts[t] = cur.fetchone()[0]
            except Exception as e:
                counts[t] = f"Error: {e}"
        debug_info["row_counts"] = counts
        
        cur.close()
        conn.close()
        return jsonify({"success": True, "diagnostics": debug_info})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
