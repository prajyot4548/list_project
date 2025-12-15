from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import oracledb
import os
import re
import traceback

# =====================================================
# PATH SETUP
# =====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# =====================================================
# FLASK APP
# =====================================================
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")
CORS(app)

# =====================================================
# ORACLE CONNECTION POOL (FAST + STABLE)
# =====================================================
pool = oracledb.create_pool(
    user="SUPP_CALL",
    password="SUPP_CALL",
    dsn="172.100.30.3:1521/OFFICE",
    min=2,
    max=6,
    increment=1
)

def get_db():
    return pool.acquire()

# =====================================================
# CLEAN SEARCH TEXT
# =====================================================
def clean_text(text):
    if not text:
        return ""
    return re.sub(r"[^a-zA-Z0-9 ]", " ", text).lower().strip()

# =====================================================
# FRONTEND ROUTES
# =====================================================
@app.route("/")
def login():
    return send_from_directory(STATIC_DIR, "login.html")

@app.route("/home")
def home():
    return send_from_directory(STATIC_DIR, "home.html")

# =====================================================
# API : FAST SEARCH
# =====================================================
@app.route("/api/tickets/CALL_DETAILS_VIEW", methods=["GET"])
def fetch_tickets():
    try:
        args = request.args
        problem  = clean_text(args.get("problem", ""))
        ticketId = args.get("ticketId")
        callId   = args.get("callId")

        db = get_db()
        cur = db.cursor()
        cur.arraysize = 300

        sql = """
        SELECT *
        FROM (
            SELECT a.*, ROW_NUMBER() OVER (ORDER BY CALL_ID DESC) rn
            FROM CALL_DETAILS_VIEW a
            WHERE 1=1
        """
        params = {}

        # EXACT SEARCH (FASTEST)
        if ticketId:
            sql += " AND TICKET_ID = :ticketId"
            params["ticketId"] = ticketId

        if callId:
            sql += " AND CALL_ID = :callId"
            params["callId"] = callId

        # TEXT SEARCH (LIMITED WORDS)
        if problem and not problem.isdigit():
            words = problem.split()[:3]
            for i, w in enumerate(words):
                sql += f"""
                AND (
                    LOWER(CALL_DETAILS) LIKE :w{i}
                    OR LOWER(SOLUTION_DETAILS) LIKE :w{i}
                )
                """
                params[f"w{i}"] = f"%{w}%"

        sql += ") WHERE rn <= 1000"

        cur.execute(sql, params)
        rows = cur.fetchall()
        cols = [c[0] for c in cur.description]
        data = [dict(zip(cols, r)) for r in rows]

        cur.close()
        db.close()

        return jsonify(data)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# =====================================================
# RUN SERVER
# =====================================================
if __name__ == "__main__":
    print("🔥 Server running at http://127.0.0.1:8080")
    app.run(host="0.0.0.0", port=8080, debug=True)
