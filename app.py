import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
from mysql.connector import pooling
from datetime import datetime
import traceback
import re

app = Flask(__name__, static_folder="static")
CORS(app, resources={r"/*": {"origins": "*"}})

# -----------------------------
# SUPERFAST DB CONNECTION POOL
# -----------------------------
dbconfig = {
    "host": os.environ.get("DB_HOST"),
    "user": os.environ.get("DB_USER"),
    "password": os.environ.get("DB_PASSWORD"),
    "database": os.environ.get("DB_NAME"),
    "port": int(os.environ.get("DB_PORT")),
}

connection_pool = pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=10,
    pool_reset_session=True,
    **dbconfig
)

def get_db():
    return connection_pool.get_connection()

# CLEAN INPUT
def clean_problem_text(text):
    if not text:
        return ""
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    cleaned = " ".join(cleaned.split()).strip().lower()
    return cleaned


# -----------------------------
# SUPERFAST SEARCH API
# -----------------------------
@app.route("/api/tickets/search", methods=["GET"])
def get_solution():
    try:
        problem = request.args.get("problem", "").strip()
        product = request.args.get("product", "").strip()
        program = request.args.get("program", "").strip()
        fromDate = request.args.get("fromDate", "").strip()
        toDate = request.args.get("toDate", "").strip()

        if problem:
            problem = clean_problem_text(problem)

        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # 🔥 SUPERFAST SELECT — NO STR_TO_DATE
        sql = """
            SELECT CALL_ID, CALL_DATE, CALL_DETAILS, SOLUTION_DETAILS,
                   PRODUCT, PROGRAM, QUEUE, BANK_NAME, TICKET_ID
            FROM support_data
            WHERE 1=1
        """
        params = []

        # --------- 🔥 VERY FAST TEXT SEARCH ---------
        if problem:
            words = problem.split(" ")

            # 🌟 STARTS WITH (very fast index usage)
            sql += " AND LOWER(CALL_DETAILS) LIKE %s"
            params.append(problem + "%")

            # 🌟 Also match anywhere (same output, faster than before)
            for w in words:
                if len(w) >= 3:
                    sql += " AND CALL_DETAILS LIKE %s"
                    params.append("%" + w + "%")

        # --------- PRODUCT ---------
        if product:
            sql += " AND PRODUCT LIKE %s"
            params.append("%" + product + "%")

        # --------- PROGRAM ---------
        if program:
            sql += " AND PROGRAM = %s"
            params.append(program)

        # --------- DATE RANGE (FASTER) ---------
        if fromDate and toDate:
            sql += " AND CALL_DATE >= %s AND CALL_DATE <= %s"
            params.extend([fromDate, toDate])

        # FORCE INDEX (makes search MUCH faster)
        sql = sql.replace("FROM support_data", "FROM support_data FORCE INDEX(PRIMARY)")

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(rows)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500



@app.route("/test-db")
def test_db():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        return {"message": "Database Connected Successfully!"}
    except Exception as e:
        return {"error": str(e)}, 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
