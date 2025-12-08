import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
from datetime import datetime
import traceback
import re

app = Flask(__name__, static_folder="static")
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route("/")
def login_page():
    return send_from_directory("static", "index.html")


@app.route("/home")
def home_page():
    return send_from_directory("static", "home.html")

# -----------------------------
# DATABASE CONNECTION (LOCAL + DEPLOY)
# -----------------------------
def get_db():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        database=os.environ.get("DB_NAME"),
        port=int(os.environ.get("DB_PORT"))
    )


# CLEAN ONLY EXTREME CHARACTERS – DO NOT REMOVE USEFUL WORDS 
def clean_problem_text(text):
    if not text:
        return ""

    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    cleaned = " ".join(cleaned.split()).strip().lower()
    return cleaned


@app.route("/api/tickets/copy of supp_data - copy", methods=["GET"])
def get_solution():
    try:
        problem = request.args.get("problem", "").strip()
        product = request.args.get("product", "").strip()
        program = request.args.get("program", "").strip()
        fromDate = request.args.get("fromDate", "").strip()
        toDate = request.args.get("toDate", "").strip()

        if problem:
            problem = clean_problem_text(problem)

        db = get_db()
        cursor = db.cursor(dictionary=True)

        sql = "SELECT * FROM `copy of supp_data - copy` WHERE 1=1"
        params = []

        if problem:
            words = problem.split(" ")
            for w in words:
                if len(w) >= 3:
                    sql += " AND LOWER(CALL_DETAILS) LIKE %s"
                    params.append(f"%{w}%")

        if product:
            sql += " AND LOWER(PRODUCT) LIKE LOWER(%s)"
            params.append(f"%{product}%")

        if program:
            sql += " AND PROGRAM = %s"
            params.append(program)

        if fromDate and toDate:
            sql += """
                AND STR_TO_DATE(CALL_DATE, '%m-%d-%Y')
                BETWEEN STR_TO_DATE(%s, '%Y-%m-%d')
                AND STR_TO_DATE(%s, '%Y-%m-%d')
            """
            params.extend([fromDate, toDate])

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        cursor.close()
        db.close()

        return jsonify(rows)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# -----------------------------
# DEPLOYMENT-FRIENDLY RUNNER
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
