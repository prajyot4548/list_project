import os
import re
import traceback
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector

# -----------------------------
# FLASK APP INIT
# -----------------------------
app = Flask(__name__, static_folder="static")
CORS(app, resources={r"/*": {"origins": "*"}})

# -----------------------------
# ROUTES FOR FRONTEND
# -----------------------------
@app.route("/")
def login_page():
    return send_from_directory("static", "index.html")


@app.route("/home")
def home_page():
    return send_from_directory("static", "home.html")


# -----------------------------
# DATABASE CONNECTION
# -----------------------------
def get_db():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        database=os.environ.get("DB_NAME"),
        port=int(os.environ.get("DB_PORT")),
        connection_timeout=10
    )


# -----------------------------
# CLEAN TEXT (SAFE SEARCH)
# -----------------------------
def clean_problem_text(text):
    if not text:
        return ""
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    return " ".join(text.split()).lower()


# ==========================================================
# API : SEARCH TICKETS (MAIN ENDPOINT)
# ==========================================================
@app.route("/api/tickets/search", methods=["GET"])
def search_tickets():
    try:
        problem = clean_problem_text(request.args.get("problem", ""))
        product = request.args.get("product", "").strip()
        program = request.args.get("program", "").strip()
        from_date = request.args.get("fromDate", "").strip()
        to_date = request.args.get("toDate", "").strip()
        ticket_id = request.args.get("ticketId", "").strip()
        bank_name = request.args.get("bankName", "").strip()

        db = get_db()
        cursor = db.cursor(dictionary=True)

        sql = "SELECT * FROM support_data WHERE 1=1"
        params = []

        # -----------------------------
        # TICKET ID (FAST + EXACT)
        # -----------------------------
        if ticket_id:
            sql += " AND TICKET_ID = %s"
            params.append(ticket_id)

        # -----------------------------
        # PROBLEM KEYWORDS
        # -----------------------------
        if problem:
            for word in problem.split():
                if len(word) >= 3:
                    sql += " AND LOWER(CALL_DETAILS) LIKE %s"
                    params.append(f"%{word}%")

        # -----------------------------
        # PRODUCT
        # -----------------------------
        if product:
            sql += " AND LOWER(PRODUCT) LIKE LOWER(%s)"
            params.append(f"%{product}%")

        # -----------------------------
        # PROGRAM (NUMERIC)
        # -----------------------------
        if program:
            sql += " AND PROGRAM = %s"
            params.append(program)

        # -----------------------------
        # BANK NAME
        # -----------------------------
        if bank_name:
            sql += " AND LOWER(BANK_NAME) LIKE LOWER(%s)"
            params.append(f"%{bank_name}%")

        # -----------------------------
        # DATE FILTER
        # -----------------------------
        if from_date and to_date:
            sql += """
                AND STR_TO_DATE(CALL_DATE, '%m-%d-%Y')
                BETWEEN STR_TO_DATE(%s, '%Y-%m-%d')
                AND STR_TO_DATE(%s, '%Y-%m-%d')
            """
            params.extend([from_date, to_date])

        # -----------------------------
        # 🚨 MEMORY SAFETY (VERY IMPORTANT)
        # -----------------------------
        sql += " ORDER BY CALL_DATE DESC LIMIT 100"

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        cursor.close()
        db.close()

        return jsonify(rows)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ==========================================================
# DB HEALTH CHECK
# ==========================================================
@app.route("/test-db")
def test_db():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return {"message": "✅ Database Connected Successfully"}
    except Exception as e:
        return {"error": str(e)}, 500


# -----------------------------
# RENDER / DEPLOY RUNNER
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
