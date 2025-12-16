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
        connection_timeout=5,
        autocommit=True
    )

# -----------------------------
# CLEAN TEXT
# -----------------------------
def clean_problem_text(text):
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    return " ".join(text.split()).lower()

# -----------------------------
# NORMALIZE TICKET ID
# -----------------------------
def normalize_ticket_id(ticket_id):
    # removes commas, spaces, symbols
    return re.sub(r"[^0-9]", "", ticket_id)

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

        if ticketId:
            ticketId = normalize_ticket_id(ticketId)

        db = get_db()
        cursor = db.cursor(dictionary=True)

        # -----------------------------
        # BASE QUERY
        # -----------------------------
        sql = "SELECT * FROM solutions.support_data WHERE 1=1"
        params = []

        # -----------------------------
        # FAST: TICKET ID SEARCH
        # -----------------------------
        if ticketId:
            sql += " AND REPLACE(TRIM(TICKET_ID), ',', '') = %s"
            params.append(ticketId)
            sql += " ORDER BY CALL_ID DESC LIMIT 1"

        else:
            # -----------------------------
            # NORMAL FILTERS
            # -----------------------------
            if bankName:
                sql += " AND BANK_NAME LIKE %s"
                params.append(f"%{bankName}%")

            if product:
                sql += " AND PRODUCT LIKE %s"
                params.append(f"%{product}%")

            if program:
                sql += " AND PROGRAM = %s"
                params.append(program)

            if fromDate:
                sql += " AND CALL_DATE >= %s"
                params.append(fromDate)

            if toDate:
                sql += " AND CALL_DATE <= %s"
                params.append(toDate)

            if problem:
                for w in problem.split():
                    if len(w) >= 3:
                        sql += " AND CALL_DETAILS LIKE %s"
                        params.append(f"%{w}%")

            sql += " ORDER BY CALL_ID DESC LIMIT 200"

        # -----------------------------
        # EXECUTE ONCE ONLY
        # -----------------------------
        cursor.execute(sql, params)
        rows = cursor.fetchall()

        cursor.close()
        db.close()

        return jsonify(rows)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# -----------------------------
# RUN (RENDER SAFE)
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
