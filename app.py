import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import oracledb
import re
import traceback

# -----------------------------
# ORACLE CLIENT INIT (DEPLOY SAFE)
# -----------------------------
# For Render / Linux / Cloud
# Set ORACLE_CLIENT_LIB in environment if needed
oracle_lib = os.environ.get("ORACLE_CLIENT_LIB")
if oracle_lib:
    oracledb.init_oracle_client(lib_dir=oracle_lib)

app = Flask(__name__, static_folder="static")
CORS(app, resources={r"/*": {"origins": "*"}})

# -----------------------------
# SERVE PAGES
# -----------------------------
@app.route("/")
def login_page():
    return send_from_directory("static", "login.html")

@app.route("/home")
def home_page():
    return send_from_directory("static", "home.html")

# -----------------------------
# ORACLE CONNECTION POOL (DEPLOY FRIENDLY)
# -----------------------------
pool = oracledb.create_pool(
    user=os.environ.get("ORACLE_USER"),
    password=os.environ.get("ORACLE_PASSWORD"),
    dsn=os.environ.get("ORACLE_DSN"),
    min=2,
    max=5,
    increment=1
)

def get_db():
    return pool.acquire()

# -----------------------------
# CLEAN USER INPUT
# -----------------------------
def clean_problem_text(text):
    if not text:
        return ""
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    return " ".join(text.split()).lower()

# ============================================================
# API : CALL DETAILS SEARCH (UNCHANGED LOGIC)
# ============================================================
@app.route("/api/tickets/CALL_DETAILS_VIEW", methods=["GET"])
def get_from_call_details():
    try:
        problem   = clean_problem_text(request.args.get("problem", ""))
        product   = request.args.get("product", "").strip()
        program   = request.args.get("program", "").strip()
        fromDate  = request.args.get("fromDate", "").strip()
        toDate    = request.args.get("toDate", "").strip()
        bankName  = request.args.get("bankName", "").strip()
        ticketId  = request.args.get("ticketId", "").strip()
        solvedBy  = request.args.get("SOLVED_BY", "").strip()
        callId    = request.args.get("callId", "").strip()

        db = get_db()
        cursor = db.cursor()
        cursor.arraysize = 200

        sql = """
        SELECT *
        FROM (
            SELECT a.*, ROW_NUMBER() OVER (ORDER BY CALL_ID DESC) rn
            FROM CALL_DETAILS_VIEW a
            WHERE 1=1
        """
        params = {}

        # ---------------- MULTI WORD SEARCH ----------------
        if problem:
            words = problem.split()
            idx = 0
            for w in words[:4]:
                if len(w) >= 3:
                    sql += f"""
                        AND (
                            LOWER(CALL_DETAILS) LIKE :w{idx}
                            OR LOWER(SOLUTION_DETAILS) LIKE :w{idx}
                        )
                    """
                    params[f"w{idx}"] = f"%{w}%"
                    idx += 1

        # ---------------- FILTERS ----------------
        if product:
            sql += " AND LOWER(PRODUCT) LIKE LOWER(:product)"
            params["product"] = f"%{product}%"

        if program:
            sql += " AND PROGRAM = :program"
            params["program"] = program

        if bankName:
            sql += " AND LOWER(BANKNAME) LIKE LOWER(:bankName)"
            params["bankName"] = f"%{bankName}%"

        if ticketId:
            sql += " AND TICKET_ID = :ticketId"
            params["ticketId"] = ticketId

        if solvedBy:
            sql += " AND LOWER(SOLVED_BY) LIKE LOWER(:solvedBy)"
            params["solvedBy"] = f"%{solvedBy}%"

        if callId:
            sql += " AND CALL_ID = :callId"
            params["callId"] = callId

        if fromDate and toDate:
            sql += """
            AND CLOSED_DATE BETWEEN
                TO_DATE(:fromDate, 'YYYY-MM-DD')
            AND TO_DATE(:toDate, 'YYYY-MM-DD') + 1
            """
            params["fromDate"] = fromDate
            params["toDate"] = toDate

        sql += """
        )
        WHERE rn <= 2000
        """

        cursor.execute(sql, params)

        rows = cursor.fetchall()
        columns = [c[0] for c in cursor.description]
        data = [dict(zip(columns, row)) for row in rows]

        cursor.close()
        db.close()

        return jsonify(data)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# -----------------------------
# DEPLOYMENT RUNNER
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print("🔥 Oracle Flask API running (DEPLOY MODE)")
    app.run(host="0.0.0.0", port=port)
