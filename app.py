import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
import traceback
import re

app = Flask(__name__, static_folder="static")
CORS(app, resources={r"/*": {"origins": "*"}})

# -----------------------------
# PAGES
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
# CLEAN TEXT
# -----------------------------
def clean_problem_text(text):
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    return " ".join(text.split()).lower()

# -----------------------------
# SEARCH API
# -----------------------------
@app.route("/api/tickets/search", methods=["GET"])
def search_tickets():
    try:
        problem   = request.args.get("problem", "").strip()
        product   = request.args.get("product", "").strip()
        program   = request.args.get("program", "").strip()
        bankName  = request.args.get("bankName", "").strip()
        ticketId  = request.args.get("ticketId", "").strip()
        fromDate  = request.args.get("fromDate", "").strip()
        toDate    = request.args.get("toDate", "").strip()

        if problem:
            problem = clean_problem_text(problem)

        db = get_db()
        cursor = db.cursor(dictionary=True)

        sql = "SELECT * FROM solutions.support_data WHERE 1=1"
        params = []

        # ---- EXACT MATCH ----
        if ticketId:
            sql += " AND TICKET_ID = %s"
            params.append(ticketId)

        # ---- BANK ----
        if bankName:
            sql += " AND LOWER(BANK_NAME) LIKE %s"
            params.append(f"%{bankName.lower()}%")

        # ---- PRODUCT ----
        if product:
            sql += " AND LOWER(PRODUCT) LIKE %s"
            params.append(f"%{product.lower()}%")

        # ---- PROGRAM ----
        if program:
            sql += " AND PROGRAM = %s"
            params.append(program)

        # ---- PROBLEM WORD MATCH ----
        if problem:
            for w in problem.split():
                if len(w) >= 3:
                    sql += " AND LOWER(CALL_DETAILS) LIKE %s"
                    params.append(f"%{w}%")

        # ---- DATE RANGE ----
        if fromDate and toDate:
            sql += """
                AND STR_TO_DATE(CALL_DATE,'%m-%d-%Y')
                BETWEEN STR_TO_DATE(%s,'%Y-%m-%d')
                AND STR_TO_DATE(%s,'%Y-%m-%d')
            """
            params.extend([fromDate, toDate])

            sql += " ORDER BY `CALL_ID` DESC LIMIT 500"

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        cursor.close()
        db.close()

        return jsonify(rows)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# -----------------------------
# TEST DB
# -----------------------------
@app.route("/test-db")
def test_db():
    try:
        conn = get_db()
        conn.close()
        return {"status": "DB CONNECTED"}
    except Exception as e:
        return {"error": str(e)}, 500

# -----------------------------
# RUN (RENDER SAFE)
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
