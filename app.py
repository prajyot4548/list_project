import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
import traceback
import re

app = Flask(__name__, static_folder="static")
CORS(app)

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
        autocommit=True
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

        db = get_db()
        cursor = db.cursor(dictionary=True)

        sql = """
        SELECT
            `ï»¿CALL_ID`,
            TICKET_ID,
            CALL_DATE,
            BANK_NAME,
            PRODUCT,
            PROGRAM,
            CALL_DETAILS,
            SOLUTION_DETAILS,
            QUEUE
        FROM solutions.support_data
        WHERE 1=1
        """
        params = []

        # ---- TICKET ID (SAFE) ----
        if ticketId:
            clean_ticket = re.sub(r"[^0-9]", "", ticketId)
            sql += " AND TRIM(REPLACE(TICKET_ID, ',', '')) = %s"
            params.append(clean_ticket)

        # ---- BANK NAME ----
        if bankName:
            sql += " AND BANK_NAME IS NOT NULL AND LOWER(BANK_NAME) LIKE %s"
            params.append(f"%{bankName.lower()}%")

        # ---- PRODUCT ----
        if product:
            sql += " AND PRODUCT IS NOT NULL AND LOWER(PRODUCT) LIKE %s"
            params.append(f"%{product.lower()}%")

        # ---- PROGRAM (NUMERIC SAFE) ----
        if program.isdigit():
            sql += " AND PROGRAM = %s"
            params.append(int(program))

        # ---- PROBLEM SEARCH ----
        if problem:
            for w in problem.split():
                if len(w) >= 3:
                    sql += " AND CALL_DETAILS IS NOT NULL AND LOWER(CALL_DETAILS) LIKE %s"
                    params.append(f"%{w}%")

        # ---- DATE FILTER (NULL SAFE) ----
        if fromDate:
            sql += """
            AND CALL_DATE IS NOT NULL
            AND STR_TO_DATE(
                CASE
                    WHEN CALL_DATE LIKE '%:%' THEN CALL_DATE
                    ELSE CONCAT(CALL_DATE, ' 00:00:00')
                END,
                '%m-%d-%Y %H:%i:%s'
            ) >= STR_TO_DATE(%s, '%Y-%m-%d')
            """
            params.append(fromDate)

        if toDate:
            sql += """
            AND CALL_DATE IS NOT NULL
            AND STR_TO_DATE(
                CASE
                    WHEN CALL_DATE LIKE '%:%' THEN CALL_DATE
                    ELSE CONCAT(CALL_DATE, ' 23:59:59')
                END,
                '%m-%d-%Y %H:%i:%s'
            ) <= STR_TO_DATE(%s, '%Y-%m-%d')
            """
            params.append(toDate)

        sql += " ORDER BY `ï»¿CALL_ID` DESC LIMIT 500"

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        cursor.close()
        db.close()

        return jsonify(rows)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
