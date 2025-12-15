import os
import re
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector

app = Flask(__name__, static_folder="static")
CORS(app)

# -----------------------------
# DATABASE CONNECTION
# -----------------------------
def get_db():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        database=os.environ.get("DB_NAME"),
        port=int(os.environ.get("DB_PORT", 3306)),
        autocommit=True
    )

# -----------------------------
# HOME ROUTES
# -----------------------------
@app.route("/")
def login():
    return send_from_directory("static", "index.html")

@app.route("/home")
def home():
    return send_from_directory("static", "home.html")

# -----------------------------
# CLEAN TEXT
# -----------------------------
def clean_text(text):
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())

# -----------------------------
# SEARCH API (OPTIMIZED)
# -----------------------------
@app.route("/api/tickets/search", methods=["GET"])
def search_tickets():
    try:
        problem = clean_text(request.args.get("problem", ""))
        ticket_id = request.args.get("ticketId", "").strip()
        program = request.args.get("program", "").strip()
        product = request.args.get("product", "").strip()
        from_date = request.args.get("fromDate", "").strip()
        to_date = request.args.get("toDate", "").strip()

        db = get_db()
        cursor = db.cursor(dictionary=True)

        sql = """
        SELECT CALL_ID, TICKET_ID, CALL_DATE, BANK_NAME, PRODUCT,
               PROGRAM, CALL_DETAILS, SOLUTION_DETAILS, QUEUE
        FROM support_data
        WHERE 1=1
        """
        params = []

        # Ticket ID (FAST – indexed)
        if ticket_id:
            sql += " AND TICKET_ID = %s"
            params.append(ticket_id)

        # Program
        if program:
            sql += " AND PROGRAM = %s"
            params.append(program)

        # Product
        if product:
            sql += " AND PRODUCT LIKE %s"
            params.append(f"%{product}%")

        # Date filter
        if from_date and to_date:
            sql += " AND CALL_DATE BETWEEN %s AND %s"
            params.extend([from_date, to_date])

        # FULLTEXT search (FAST)
        if problem:
            sql += """
            AND MATCH(CALL_DETAILS, SOLUTION_DETAILS)
            AGAINST (%s IN BOOLEAN MODE)
            """
            params.append(problem)

        # IMPORTANT: LIMIT
        sql += " ORDER BY CALL_ID DESC LIMIT 100"

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        cursor.close()
        db.close()

        return jsonify(rows)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -----------------------------
# TEST DB
# -----------------------------
@app.route("/test-db")
def test_db():
    try:
        db = get_db()
        db.close()
        return {"message": "Database Connected"}
    except Exception as e:
        return {"error": str(e)}, 500

# -----------------------------
# RUN (RENDER SAFE)
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
