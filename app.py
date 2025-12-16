import os, re, traceback
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector

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
# DB CONNECTION
# -----------------------------
def get_db():
    return mysql.connector.connect(
        host=os.environ["DB_HOST"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        port=int(os.environ["DB_PORT"]),
        autocommit=True
    )

# -----------------------------
# SEARCH API (FAST & SAFE)
# -----------------------------
@app.route("/api/tickets/search", methods=["GET"])
def search_tickets():
    try:
        args = request.args

        ticketId = re.sub(r"[^0-9]", "", args.get("ticketId", ""))
        bankName = args.get("bankName", "").strip().lower()
        product  = args.get("product", "").strip().lower()
        program  = args.get("program", "").strip()
        problem  = args.get("problem", "").strip().lower()
        fromDate = args.get("fromDate", "")
        toDate   = args.get("toDate", "")

        sql = """
        SELECT *
        FROM support_data
        WHERE 1=1
        """
        params = []

        # 🔥 Ticket ID (FAST & SAFE)
        if ticketId:
            sql += " AND REPLACE(`TICKET_ID`, ',', '') = %s"
            params.append(ticketId)

        if bankName:
            sql += " AND LOWER(BANK_NAME) LIKE %s"
            params.append(f"%{bankName}%")

        if product:
            sql += " AND LOWER(PRODUCT) LIKE %s"
            params.append(f"%{product}%")

        if program:
            sql += " AND PROGRAM = %s"
            params.append(program)

        if problem:
            for w in problem.split():
                if len(w) >= 3:
                    sql += " AND LOWER(CALL_DETAILS) LIKE %s"
                    params.append(f"%{w}%")

        # DATE FILTER (safe with your text dates)
        if fromDate:
            sql += " AND STR_TO_DATE(CALL_DATE,'%m-%d-%Y') >= %s"
            params.append(fromDate)

        if toDate:
            sql += " AND STR_TO_DATE(CALL_DATE,'%m-%d-%Y') <= %s"
            params.append(toDate)

        # ✅ ORDER USING YOUR EXISTING COLUMN
        sql += " ORDER BY CAST(REPLACE(`ï»¿CALL_ID`, ',', '') AS UNSIGNED) DESC LIMIT 500"

        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        db.close()

        return jsonify(rows)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
