from multiprocessing.resource_tracker import getfd
import matplotlib.pyplot as plt
import io
import base64
from flask import Flask, render_template, request, redirect, flash, session, url_for, send_file,jsonify,make_response
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from datetime import datetime
import math
import time
import pandas as pd
import zipfile
import sys
import click
import webview
import hashlib
from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
from dateutil.relativedelta import relativedelta
import sqlite3

# ✅ Automatically parses both date and datetime formats
from dateutil import parser
from flask import request, redirect, url_for, render_template, flash
from utils.auth_decorator import login_required
from datetime import datetime




# Ensure stdout is set up
sys.stdout = sys.__stdout__


app = Flask(__name__)
app.secret_key = "your_secret_key"



# Ensure database directory exists
os.makedirs("db", exist_ok=True)

DB_PATH = os.path.join(os.path.abspath(os.getcwd()), "bank.db")

db_path = r"C:\Users\kiran\Desktop\BMS_Application\db\bank.db"

try:
    conn = sqlite3.connect(db_path)
    print("Database opened successfully")
    conn.close()
except Exception as e:
    print("Error:", e)

# Database connection helper
def get_db_connection():
    conn = sqlite3.connect('db/bank.db', timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    """Initialize database tables if they don't exist"""
    conn = get_db_connection()
    cursor = conn.cursor()



# Helper Functions
def get_db_connection():
    conn = sqlite3.connect('db/bank.db')
    conn.row_factory = sqlite3.Row
    return conn

from functools import wraps


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf", "doc", "docx", "xls", "xlsx"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
 
@app.route("/")
def home():
    if "admin_id" not in session:
        flash("Please login to access this page.", "warning")
    return redirect(url_for("login"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            flash("Passwords do not match!")
            return redirect("/signup")

        conn = get_db_connection()
        try:
            hashed_password = generate_password_hash(password)
            conn.execute("INSERT INTO admins (username, password) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            flash("Signup successful! Please login.")
            return redirect("/login")
        except sqlite3.IntegrityError:
            flash("Username already exists!")
        finally:
            conn.close()

    return render_template("signup.html")





@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        admin = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
        conn.close()

        if admin and check_password_hash(admin["password"], password):
            session["admin_id"] = admin["id"]
            session["username"] = admin["username"]
            flash("Login successful!")
            return redirect("/admin_dashboard")
        else:
            flash("Invalid credentials! Please try again.")
            return redirect("/login")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.permanent = False
    session.clear()
    flash("You have been logged out.")
    return redirect("/login")




@app.route("/generate_report")
@login_required
def bank_report():
    conn = get_db_connection()
    try:
        # -- Fetch detailed records
        accounts = [dict(row) for row in conn.execute("""
            SELECT id, full_name, phone, account_type, balance AS total_balance FROM accounts
        """).fetchall()]

        loans = [dict(row) for row in conn.execute("""
            SELECT loans.id, a.full_name, loan_type, loan_amount, interest_rate, nominee_name, nominee_id
            FROM loans INNER JOIN accounts a ON loans.account_id = a.id
        """).fetchall()]

        fixed_deposits = [dict(row) for row in conn.execute("""
            SELECT fd_accounts.fd_id, a.full_name, fd_amount, interest_rate, maturity_date
            FROM fd_accounts INNER JOIN accounts a ON fd_accounts.account_id = a.id
        """).fetchall()]

        transactions = [dict(row) for row in conn.execute("""
            SELECT transactions.id, a.full_name, transaction_type, amount, transactions.timestamp
            FROM transactions INNER JOIN accounts a ON transactions.account_id = a.id
        """).fetchall()]

        closed_accounts = [dict(row) for row in conn.execute("""
            SELECT id, full_name, account_type, closed_at FROM closed_accounts
        """).fetchall()]

        # -- Summary statistics
        expenditure = conn.execute("SELECT IFNULL(SUM(amount), 0) FROM expenditures").fetchone()[0] or 0.0
        active_accounts = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
        closed_accounts_count = conn.execute("SELECT COUNT(*) FROM closed_accounts").fetchone()[0]
        total_transactions = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        total_loans = conn.execute("SELECT SUM(loan_amount) FROM loans").fetchone()[0] or 0.0

        # -- Fee summaries
        admin_fee = conn.execute("SELECT SUM(admin_fee) FROM accounts").fetchone()[0] or 0.0
        share_fee = conn.execute("SELECT SUM(share_fee) FROM accounts").fetchone()[0] or 0.0
        file_charge_fee = conn.execute("SELECT SUM(file_charge_fee) FROM accounts").fetchone()[0] or 0.0
        loan_file_charge = conn.execute("SELECT SUM(file_charge) FROM loans").fetchone()[0] or 0.0

        # -- Total balance includes share/admin/file fees
        total_balance = conn.execute("""
            SELECT SUM(balance + share_fee + admin_fee + file_charge_fee) 
            FROM accounts
        """).fetchone()[0] or 0.0

        # -- Profit/Loss (simple estimate)
        profit_loss = total_balance - total_loans

    finally:
        conn.close()

    # -- Bar graph
    graph_data = {
        "Active Accounts": active_accounts,
        "Closed Accounts": closed_accounts_count,
        "Total Transactions": total_transactions,
        "Total Loans": total_loans,
        "Profit/Loss": profit_loss,
        "Expenditure": expenditure,
        "Admin Fees": admin_fee,
        "File Charges": file_charge_fee,
        "Loan File Charges": loan_file_charge,
        "Share Fees": share_fee
    }

    # -- Generate Graph
    img = io.BytesIO()
    plt.figure(figsize=(10, 4))
    plt.bar(graph_data.keys(), graph_data.values(),
            color=['green', 'red', 'blue', 'purple', 'orange', 'cyan', 'gray', 'teal', 'gold', 'pink'])
    plt.title("Bank Summary Report")
    plt.ylabel("Amount / Count")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(img, format='png')
    img.seek(0)
    graph_url = base64.b64encode(img.getvalue()).decode('utf8')
    img.close()

    return render_template("report.html",
                           accounts=accounts,
                           loans=loans,
                           fixed_deposits=fixed_deposits,
                           transactions=transactions,
                           closed_accounts=closed_accounts,
                           active_accounts=active_accounts,
                           closed_accounts_count=closed_accounts_count,
                           total_transactions=total_transactions,
                           total_loans=total_loans,
                           profit_loss=profit_loss,
                           total_balance=total_balance,
                           expenditure=expenditure,
                           admin_fee=admin_fee,
                           file_charge_fee=file_charge_fee,
                           share_fee=share_fee,
                           loan_file_charge=loan_file_charge,
                           graph_url=graph_url)
    
    
@app.route("/admin_dashboard")
@login_required
def admin_dashboard():
    return render_template("admin_dashboard.html", username=session.get("username"))






@app.route("/create_account", methods=["GET", "POST"])
@login_required
def create_account():
    if request.method == "POST":
        try:
            form_data = {
                "full_name": request.form.get("full_name", "").strip(),
                "father_name": request.form.get("father_name", "").strip(),
                "phone": request.form.get("phone", "").strip(),
                "dob": request.form.get("dob", "").strip(),
                "address": request.form.get("address", "").strip(),
                "account_type": request.form.get("account_type", "").lower(),
                "balance": float(request.form.get("balance", 0) or 0),
                "share_fee": float(request.form.get("share_fee", 0) or 0),
                "total_shares": float(request.form.get("total_shares", 0) or 0),
                "admin_fee": float(request.form.get("admin_fee", 0) or 0),
                "school_name": request.form.get("school_name", "").strip()

            }

            if not all([form_data["full_name"], form_data["father_name"], form_data["phone"], form_data["account_type"]]):
                flash("Missing required fields", "danger")
                return redirect(url_for("create_account"))

            account_number = generate_account_number(form_data["account_type"])  # Make sure this function exists

            conn = get_db_connection()
            conn.execute("""
                INSERT INTO accounts (
                    account_number, full_name, father_name, phone, dob,
                    address, account_type, balance, share_fee, total_shares,admin_fee, school_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?)
            """, (
                account_number,
                form_data["full_name"],
                form_data["father_name"],
                form_data["phone"],
                form_data["dob"],
                form_data["address"],
                form_data["account_type"],
                form_data["balance"],
                form_data["share_fee"],
                form_data["total_shares"],
                form_data["admin_fee"],
                form_data["school_name"]
            ))
            conn.commit()
            conn.close()

            flash(f"Account created successfully! Account #: {account_number}", "success")
            return redirect(url_for("accounts"))

        except Exception as e:
            flash(f"Unexpected error: {str(e)}", "danger")

    return render_template("create_account.html")


 
def generate_account_number(account_type):
    prefix = {
        'savings': '00',
        'current': '00',
        'fixed deposit': '00'
        
    
    }.get(account_type, 'ACC')
    return f"{prefix}-{str(uuid.uuid4().int)[:3]}"

account_counters = {
    'savings': 0,
    'current': 0,
    'fixed deposit': 0
}



# Route to Edit Account
@app.route("/edit_account/<int:account_id>", methods=["GET", "POST"])
@login_required
def edit_account(account_id): 
    conn = get_db_connection()
    account = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()

    if request.method == "POST":
        print("Form Data:", request.form)  # Debugging

        # Safely get form data
        full_name = request.form.get("full_name", "")
        father_name = request.form.get("father_name", "")
        phone = request.form.get("phone", "")
        dob = request.form.get("dob", "")
        address = request.form.get("address", "")
        account_type = request.form.get("account_type", "")
        balance = float(request.form.get("balance", 0) or 0)
        total_shares = request.form.get("total_shares",  "")
        share_fee = float(request.form.get("share_fee", 0) or 0)
        admin_fee = float(request.form.get("admin_fee", 0) or 0)

        conn.execute("""
            UPDATE accounts
            SET full_name = ?, father_name = ?, phone = ?, dob = ?, address = ?, 
                account_type = ?, balance = ?, share_fee = ?, total_shares = ?, admin_fee = ?
            WHERE id = ?
        """, (full_name, father_name, phone, dob, address, account_type, balance, share_fee, total_shares, admin_fee, account_id))
        
        conn.commit()
        conn.close()
        
        flash("Account updated successfully!", "success")
        return redirect(url_for("accounts"))

    conn.close()
    
    return render_template("edit_account.html", account=account)


    
# Route to List All Accounts
@app.route("/accounts")
@login_required
def accounts():
    with get_db_connection() as conn:
        accounts = conn.execute("SELECT * FROM accounts").fetchall()
    return render_template("accounts.html", accounts=accounts)

# Route to Delete Account
@app.route("/delete_account/<int:account_id>")

def delete_account(account_id):
    conn = get_db_connection()
    with get_db_connection() as conn:
        conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        conn.commit()
    
    flash("Account deleted successfully!", "success")
    return redirect(url_for("accounts"))

@app.route("/transaction", methods=["GET", "POST"])
@login_required
def transaction():
    if request.method == "POST":
        account_id = request.form["account_id"]
        amount = float(request.form["amount"])
        transaction_type = request.form["transaction_type"]  # Deposit or Withdrawal
        if amount <= 0:
            flash("Amount must be greater than 0!")
            return redirect("/transaction")

        conn = get_db_connection()
        
        # Fetch account balance
        account = conn.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,)).fetchone()

        if not account:
            flash("Invalid account!")
            conn.close()
            return redirect("/transaction")

        current_balance = account["balance"]

        if transaction_type == "Deposit":
            new_balance = current_balance + amount
            transaction_amount = amount  # Store as positive value
            flash("Deposit successful!")

        elif transaction_type == "Withdrawal":
            if current_balance >= amount:
                new_balance = current_balance - amount
                transaction_amount = -amount  # Store as negative value
                flash("Withdrawal successful!")
            else:
                flash("Insufficient funds!")
                conn.close()
                return redirect("/transaction")

        
        
        
        
        
        # Update account balance
        conn.execute("UPDATE accounts SET balance = ? WHERE id = ?", (new_balance, account_id))
        
        # Insert transaction record with signed value and transaction type
        conn.execute("""
            INSERT INTO transactions (account_id, transaction_type, amount)
            VALUES (?, ?, ?)
        """, (account_id, transaction_type, transaction_amount))  # Include transaction_type
        
        conn.commit()
        conn.close()
        return redirect("/transaction")

    conn = get_db_connection()
    accounts = conn.execute("SELECT * FROM accounts").fetchall()
    conn.close()
    return render_template("transaction.html", accounts=accounts)
# Route to display transactions for a specific account


@app.route("/account/statement/<int:account_id>")
@login_required
def account_statement(account_id):
    conn = get_db_connection()
    try:
        # Get account details
        account = conn.execute(
            "SELECT id, full_name, balance FROM accounts WHERE id = ?",
            (account_id,)
        ).fetchone()
        
        if not account:
            flash("Account not found!", "danger")
            return redirect(url_for("account_list"))
        
        # Get last 10 transactions
        transactions = conn.execute(
            """SELECT id, transaction_type, amount, timestamp 
               FROM transactions 
               WHERE account_id = ?
               ORDER BY timestamp DESC
               LIMIT 10""",
            (account_id,)
        ).fetchall()
        
        return render_template(
            "mini_statement.html",
            account=account,  # Changed from Accounts to account
            transactions=transactions
        )
    except Exception as e:
        flash(f"Error fetching statement: {str(e)}", "danger")
        return redirect(url_for("account_list"))
    finally:
        conn.close()







@app.route('/account_list')
@login_required
def account_list():
    conn = get_db_connection()
    accounts = conn.execute('SELECT * FROM accounts').fetchall()
    with get_db_connection() as conn:
        accounts = conn.execute('SELECT * FROM accounts').fetchall()
    return render_template('account_list.html', accounts=accounts)



@app.route("/transfer", methods=["GET", "POST"])
@login_required
def transfer():
    conn = get_db_connection()
    if request.method == "POST":
        from_id = int(request.form["from_account"])
        to_id = int(request.form["to_account"])
        amount = float(request.form["amount"])
        note = request.form.get("note", "")

        from_ac = conn.execute("SELECT * FROM accounts WHERE id = ?", (from_id,)).fetchone()
        to_ac = conn.execute("SELECT * FROM accounts WHERE id = ?", (to_id,)).fetchone()

        if from_id == to_id:
            flash("Cannot transfer to the same account.", "warning")
            return redirect(url_for("transfer"))

        if from_ac["balance"] < amount:
            flash("Insufficient balance in source account.", "danger")
            return redirect(url_for("transfer"))

        # Deduct from sender
        conn.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, from_id))
        conn.execute("INSERT INTO transactions (account_id, transaction_type, amount, note) VALUES (?, ?, ?, ?)",
                     (from_id, "transfer_out", amount, note))

        # Add to receiver
        conn.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, to_id))
        conn.execute("INSERT INTO transactions (account_id, transaction_type, amount, note) VALUES (?, ?, ?, ?)",
                     (to_id, "transfer_in", amount, note))

        conn.commit()
        conn.close()
        flash("Transfer completed successfully.", "success")
        return redirect(url_for("dashboard"))

    accounts = conn.execute("SELECT * FROM accounts").fetchall()
    return render_template("transfer.html", accounts=accounts)





@app.route("/transactions/<int:account_id>")
@login_required
def view_transactions(account_id):
    conn = get_db_connection()
    txns = conn.execute("SELECT * FROM transactions WHERE account_id = ? ORDER BY timestamp DESC", (account_id,)).fetchall()
    conn.close()
    with get_db_connection() as conn:
        txns = conn.execute("SELECT * FROM transactions WHERE account_id = ? ORDER BY timestamp DESC", (account_id,)).fetchall()
    return render_template("transactions.html", txns=txns)
@login_required
def view_mini_statement(account_id):
    conn = get_db_connection()
    account = conn.execute('SELECT * FROM accounts WHERE id = ?', (account_id,)).fetchone()
    transactions_raw = conn.execute(
        'SELECT * FROM transactions WHERE account_id = ? ORDER BY timestamp DESC LIMIT 10',
        (account_id,)
    ).fetchall()
    conn.close()

    if account is None:
        return "Account not found", 404

    transactions = []
    for txn in transactions_raw:
        txn_dict = dict(txn)
        try:
            txn_dict['timestamp'] = datetime.strptime(txn_dict['timestamp'], "%Y-%m-%d %H:%M:%S")
        except Exception:
            txn_dict['timestamp'] = datetime.now()
        transactions.append(txn_dict)

    return render_template('transactions.html', account=account, transactions=transactions)




@app.route("/transactions/full/<int:account_id>")
@login_required
def view_full_transaction_history(account_id):
    conn = get_db_connection()
    transactions = conn.execute("""
        SELECT 
            t.*, 
            a.account_number, 
            a.full_name AS customer_name, 
            a.balance 
        FROM transactions t 
        JOIN accounts a ON t.account_id = a.id 
        WHERE t.account_id = ?
        ORDER BY t.timestamp DESC
    """, (account_id,)).fetchall()

    account = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
    conn.close()

    if not account:
        return "Account not found", 404

    return render_template("transactions.html", account=account, transactions=transactions)


@app.route('/transactions/recent/<int:account_id>')
@login_required
def recent_transactions(account_id):
    conn = get_db_connection()
    transactions = conn.execute("""
        SELECT 
            t.*, 
            a.account_number, 
            a.full_name AS customer_name 
        FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        WHERE t.account_id = ?
        ORDER BY t.timestamp DESC
        LIMIT 5
    """, (account_id,)).fetchall()

    account = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
    conn.close()

    if not account:
        flash("Account not found!", "danger")
        return redirect(url_for("dashboard"))

    return render_template("recent_transactions.html", transactions=transactions, account=account)





# @app.route("/transaction")
# @login_required
# def transaction():
#     conn = get_db_connection()
#     accounts = conn.execute("SELECT * FROM accounts").fetchall()

#     # ✅ Fetch recent transactions
#     transactions = conn.execute("""
#         SELECT t.*, a.account_number, a.full_name 
#         FROM transactions t 
#         JOIN accounts a ON t.account_id = a.id 
#         ORDER BY t.timestamp DESC 
#         LIMIT 10
#     """).fetchall()

#     conn.close()

#     return render_template("transaction.html", accounts=accounts, transactions=transactions)



# @app.route("/transaction")
# @login_required
# def transaction():
#     conn = get_db_connection()
#     accounts = conn.execute("SELECT * FROM accounts").fetchall()

#     transactions = conn.execute("""
#         SELECT t.*, a.account_number, a.full_name
#         FROM transactions t
#         JOIN accounts a ON t.account_id = a.id
#         ORDER BY t.timestamp DESC
#         LIMIT 10
#     """).fetchall()

#     conn.close()
#     return render_template("transaction.html", accounts=accounts, transactions=transactions)





from datetime import datetime
import math

@app.route("/loans", methods=["GET", "POST"])
@login_required
def loans():
    if "admin_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("login"))

    if request.method == "POST":
        try:
            conn = get_db_connection()
            account_id = request.form["account_id"]

            # ✅ Validate account exists
            account = conn.execute("SELECT id FROM accounts WHERE id = ?", (account_id,)).fetchone()
            if not account:
                flash("Error: Account ID does not exist!", "danger")
                return redirect(url_for("loans"))

            # ✅ Fetch form data
            loan_type = request.form["loan_type"]
            loan_amount = float(request.form["loan_amount"])
            interest_rate = float(request.form["interest_rate"])
            nominee_name = request.form["nominee_name"]
            nominee_id = request.form["nominee_id"]
            file_charge = float(request.form.get("file_charge", 0))

            # ✅ Dates
            start_date = datetime.strptime(request.form["start_date"], "%Y-%m-%d")
            end_date = datetime.strptime(request.form["end_date"], "%Y-%m-%d")
            total_days = (end_date - start_date).days

            if total_days <= 0:
                flash("End date must be after start date.", "danger")
                return redirect(url_for("loans"))

            # ✅ EMI Calculation with daily interest
            def calculate_daily_emi(amount, rate, days):
                daily_rate = (rate / 100) / 365
                if daily_rate == 0:
                    return amount / days
                emi = (amount * daily_rate * math.pow(1 + daily_rate, days)) / \
                      (math.pow(1 + daily_rate, days) - 1)
                return round(emi, 2)

            emi = calculate_daily_emi(loan_amount, interest_rate, total_days)
            remaining_balance = round(emi * total_days, 2)

            # ✅ Insert Loan Record
            conn.execute("""
                INSERT INTO loans (
                    account_id, loan_type, loan_amount, interest_rate, loan_term,
                    nominee_name, nominee_id, file_charge, insert_amount, remaining_balance,
                    start_date, end_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                account_id, loan_type, loan_amount, interest_rate, total_days,
                nominee_name, nominee_id, file_charge, emi, remaining_balance,
                start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
            ))

            conn.commit()
            conn.close()

            flash(f"Loan granted successfully! EMI: ₹{emi}/day", "success")
            return redirect(url_for("loan_holders"))

        except ValueError as e:
            flash(f"Input error: {str(e)}", "danger")
            return redirect(url_for("loans"))

    return render_template("loans.html")







@app.route("/loan_details/<int:loan_id>")
@login_required
def loan_details(loan_id):
    conn = get_db_connection()
    loan = conn.execute("SELECT * FROM loans WHERE id = ?", (loan_id,)).fetchone()
    emi_history = conn.execute("SELECT * FROM emi_payments WHERE loan_id = ?", (loan_id,)).fetchall()
    conn.close()

    if not loan:
        flash("Loan not found!", "danger")
        return redirect(url_for("loan_holders"))

    return render_template("loan_details.html", loan=loan, emi_history=emi_history)


# ✅ Edit Loan Route (Fixing the Missing Route)
@app.route("/edit_loan/<int:loan_id>", methods=["GET", "POST"])
@login_required
def edit_loan(loan_id):
    conn = get_db_connection()
    loan = conn.execute("SELECT * FROM loans WHERE id = ?", (loan_id,)).fetchone()

    if not loan:
        flash("Loan not found!", "danger")
        return redirect(url_for("loan_holders"))

    if request.method == "POST":
        try:
            loan_type = request.form["loan_type"]
            loan_amount = float(request.form["loan_amount"])
            interest_rate = float(request.form["interest_rate"])
            loan_term = int(request.form["loan_term"])
            nominee_name = request.form["nominee_name"]
            nominee_id = request.form["nominee_id"]
            remaining_balance = float(request.form["remaining_balance"])

            conn.execute("""
                UPDATE loans
                SET loan_type = ?, loan_amount = ?, interest_rate = ?, loan_term = ?, 
                    nominee_name = ?, nominee_id = ?, remaining_balance = ?
                WHERE id = ?
            """, (loan_type, loan_amount, interest_rate, loan_term, nominee_name, nominee_id, remaining_balance, loan_id))

            conn.commit()
            conn.close()

            flash("Loan details updated successfully!", "success")
            return redirect(url_for("loan_details", loan_id=loan_id))

        except ValueError:
            flash("Invalid input. Please enter valid numbers.", "danger")

    return render_template("edit_loan.html", loan=loan)



# # ✅ Display Loan Holders
# @app.route("/loan_holders")
# @login_required
# def loan_holders():
#     conn = get_db_connection()
#     results = conn.execute("""
#         SELECT l.id AS loan_id, a.full_name, a.phone, l.loan_type, l.loan_amount, 
#         l.file_charge,
#                l.insert_amount, l.loan_term, l.interest_rate, l.nominee_name, 
#                l.nominee_id, l.remaining_balance, l.timestamp, l.start_date, l.end_date
#         FROM loans l
#         INNER JOIN accounts a ON l.account_id = a.id
#     """).fetchall()
#     conn.close()
#     return render_template("loan_holders.html", results=results)












@app.route("/loan_holders")
@login_required
def loan_holders():
    conn = get_db_connection()
    loans = conn.execute("""
        SELECT 
            loans.id AS loan_id,
            accounts.full_name,
            accounts.phone,
            loans.loan_type,
            loans.loan_amount,
            loans.file_charge,
            loans.interest_rate,
            loans.remaining_balance,
            loans.loan_term,
            loans.start_date,
            loans.end_date
        FROM loans
        JOIN accounts ON loans.account_id = accounts.id
    """).fetchall()
    conn.close()
    return render_template("loan_holders.html", results=loans)





def calculate_interest(principal, rate, days):
    """Calculate interest for a given period"""
    return principal * days * (rate / 36500)

@app.route("/premium_emi/<int:loan_id>", methods=["GET", "POST"])
@login_required
def premium_emi(loan_id):
    conn = get_db_connection()
    
    # Get loan with customer details
    loan = conn.execute("""
        SELECT loans.*, accounts.full_name, accounts.phone 
        FROM loans 
        JOIN accounts ON loans.account_id = accounts.id 
        WHERE loans.id = ?
    """, (loan_id,)).fetchone()
    
    if not loan:
        flash("Loan not found.", "danger")
        return redirect(url_for("loan_holders"))

    if not loan["start_date"]:
        flash("Loan start date is missing. Please update the loan.", "danger")
        return redirect(url_for("loan_details", loan_id=loan_id))

    # Calculate total paid amount
    total_paid = conn.execute(
        "SELECT SUM(emi_amount) FROM emi_payments WHERE loan_id = ?", 
        (loan_id,)
    ).fetchone()[0] or 0.0
    
    # Add paid amount to loan data
    loan = dict(loan)
    loan["paid_amount"] = total_paid
    
    # Get payments
    payments = conn.execute(
        "SELECT * FROM emi_payments WHERE loan_id = ? ORDER BY payment_date", 
        (loan_id,)
    ).fetchall()

    if request.method == "POST":
        try:
            emi_amount = float(request.form["emi_amount"])
            payment_date = request.form["payment_date"]
            
            if emi_amount <= 0:
                raise ValueError("EMI must be positive.")
                
            # Store only date part
            payment_date = payment_date[:10]
            
            # Insert payment
            conn.execute(
                "INSERT INTO emi_payments (loan_id, emi_amount, payment_date) VALUES (?, ?, ?)",
                (loan_id, emi_amount, payment_date)
            )
            conn.commit()
            flash("Payment recorded successfully!", "success")
            return redirect(url_for("premium_emi", loan_id=loan_id))
            
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")

    # Generate EMI table
    table, remaining = generate_emi_table(loan, payments)
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    conn.close()
    return render_template(
        "premium_emi.html",
        loan=loan,
        emi_table=table,
        remaining_principal=remaining,
        current_date=current_date
    )

def generate_emi_table(loan, payments):
    """Generate EMI payment history table"""
    if not loan["start_date"]:
        raise ValueError("Loan start_date is missing.")

    # Parse dates
    start_date = parser.parse(loan["start_date"])
    principal = float(loan["loan_amount"])
    rate = float(loan["interest_rate"])
    remaining = principal
    last_date = start_date
    interest_due = 0
    table = []

    for pay in payments:
        pay = dict(pay)
        pay_date = parser.parse(pay["payment_date"])
        
        # Calculate days since last payment
        days = (pay_date - last_date).days
        if days < 0:
            continue  # Skip invalid dates
            
        # Calculate interest for this period
        interest = calculate_interest(remaining, rate, days)
        interest_due += interest
        
        # Process payment
        credit = float(pay["emi_amount"])
        interest_paid = min(credit, interest_due)
        principal_paid = credit - interest_paid
        interest_due -= interest_paid
        remaining = max(0, remaining - principal_paid)
        
        # Add to table
        table.append({
            "date": pay_date.strftime("%Y-%m-%d"),
            "days": days,
            "interest": interest,
            "credit": credit,
            "interest_paid": interest_paid,
            "principal_paid": principal_paid,
            "remaining_principal": remaining
        })
        
        
        last_date = pay_date

    return table, remaining



@app.route("/create_fd", methods=["GET", "POST"])
@login_required
def create_fd_account():
    if request.method == "POST":
        account_id = request.form["account_id"]
        fd_amount = float(request.form["fd_amount"])
        interest_rate = float(request.form["interest_rate"])
        if fd_amount <= 0 or interest_rate <= 0:
            flash("Amount and interest rate must be greater than 0!")
            return redirect("/create_fd")
        # Ensure maturity date is in the future
        fd_date = datetime.strptime(request.form["maturity_date"], "%Y-%m-%d")
        if fd_date <= datetime.now():
            flash("Maturity date must be in the future!")
            return redirect("/create_fd")
        maturity_date = request.form["maturity_date"]

        # Calculate interest and total amount
        interest_amount = fd_amount * (interest_rate / 100)
        total_amount = fd_amount + interest_amount

        # Save FD account details in the database
        conn = get_db_connection()
        conn.execute("""
    INSERT INTO fd_accounts (
        account_id, amount, interest_rate, maturity_date, fd_date, interest_amount, total_amount
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
""", (
    account_id,
    fd_amount,
    interest_rate,
    maturity_date,
    fd_date,
    interest_amount,
    total_amount
))
        conn.commit()
        conn.close()

        flash("Fixed Deposit account created successfully!")
        return redirect("/admin_dashboard")
    return render_template("create_fd.html")


@app.route("/view_fd/<int:fd_id>")
@login_required
def view_fd(fd_id):
    conn = get_db_connection()
    fd = conn.execute("SELECT * FROM fd_accounts WHERE fd_id = ?", (fd_id,)).fetchone()
    conn.close()
    return render_template("view_fd.html", fd=fd)  # Template for viewing the FD details

@app.route("/edit_fd/<int:fd_id>", methods=["GET", "POST"])
@login_required
def edit_fd(fd_id):
    conn = get_db_connection()
    fd = conn.execute("SELECT * FROM fd_accounts WHERE fd_id = ?", (fd_id,)).fetchone()

    if request.method == "POST":
        # Collect form data
        account_id = request.form["account_id"]
        fd_amount = request.form["fd_amount"]
        interest_rate = request.form["interest_rate"]
        interest_amount = request.form["interest_amount"]
        total_amount = request.form["total_amount"]
        fd_date = request.form["fd_date"]
        maturity_date = request.form["maturity_date"]

        # Update the record in the database
        conn.execute("""
            UPDATE fd_accounts 
            SET account_id = ?, amount = ?, interest_rate = ?, 
                interest_amount = ?, total_amount = ?, fd_date = ?, maturity_date = ?
            WHERE fd_id = ?
        """, (account_id, fd_amount, interest_rate, interest_amount, total_amount, fd_date, maturity_date, fd_id))

        conn.commit()
        conn.close()

        return redirect(url_for("view_fd", fd_id=fd_id))

    conn.close()
    return render_template("edit_fd.html", fd=fd)

# #-----------------------------------------
# # Create FD Account
# # -----------------------------------------
# @app.route("/create_fd", methods=["GET", "POST"])
# @login_required
# def create_fd_account():
#     if request.method == "POST":
#         try:
#             account_id = request.form["account_id"]
#             fd_amount = float(request.form["fd_amount"])
#             interest_rate = float(request.form["interest_rate"])
#             fd_date = datetime.now()

#             # Validate maturity date
#             maturity_date = datetime.strptime(request.form["maturity_date"], "%Y-%m-%d")
#             if maturity_date <= datetime.now():
#                 flash("Maturity date must be in the future!", "danger")
#                 return redirect("/create_fd")

#             # Calculate interest and total
#             interest_amount = fd_amount * (interest_rate / 100)
#             total_amount = fd_amount + interest_amount

#             # Insert into DB
#             conn = get_db_connection()
#             conn.execute("""
#                 INSERT INTO fd_accounts (
#                     account_id, amount, interest_rate, maturity_date,
#                     fd_date, interest_amount, total_amount
#                 ) VALUES (?, ?, ?, ?, ?, ?, ?)
#             """, (
#                 account_id, fd_amount, interest_rate, maturity_date.strftime("%Y-%m-%d"),
#                 fd_date.strftime("%Y-%m-%d"), interest_amount, total_amount
#             ))
#             conn.commit()
#             flash("FD Account created successfully!", "success")
#             return redirect("/admin_dashboard")
#         except Exception as e:
#             flash(f"Error: {str(e)}", "danger")
#         finally:
#             conn.close()

#     return render_template("create_fd.html")

# # -----------------------------------------
# # View FD Account
# # -----------------------------------------
# @app.route("/view_fd/<int:fd_id>")
# @login_required
# def view_fd(fd_id):
#     conn = get_db_connection()
#     fd = conn.execute("SELECT * FROM fd_accounts WHERE fd_id = ?", (fd_id,)).fetchone()
#     conn.close()
#     return render_template("view_fd.html", fd=fd)

# # -----------------------------------------
# # Edit FD Account
# # -----------------------------------------
# @app.route("/edit_fd/<int:fd_id>", methods=["GET", "POST"])
# @login_required
# def edit_fd(fd_id):
#     conn = get_db_connection()
#     fd = conn.execute("SELECT * FROM fd_accounts WHERE fd_id = ?", (fd_id,)).fetchone()

#     if request.method == "POST":
#         try:
#             account_id = request.form["account_id"]
#             fd_amount = float(request.form["fd_amount"])
#             interest_rate = float(request.form["interest_rate"])
#             interest_amount = float(request.form["interest_amount"])
#             total_amount = float(request.form["total_amount"])
#             fd_date = request.form["fd_date"]
#             maturity_date = request.form["maturity_date"]

#             conn.execute("""
#                 UPDATE fd_accounts SET
#                     account_id = ?, amount = ?, interest_rate = ?,
#                     interest_amount = ?, total_amount = ?, fd_date = ?, maturity_date = ?
#                 WHERE fd_id = ?
#             """, (
#                 account_id, fd_amount, interest_rate,
#                 interest_amount, total_amount,
#                 fd_date, maturity_date, fd_id
#             ))
#             conn.commit()
#             flash("FD Account updated successfully!", "success")
#             return redirect(url_for("view_fd", fd_id=fd_id))
#         except Exception as e:
#             flash(f"Error: {str(e)}", "danger")
#         finally:
#             conn.close()

#     conn.close()
#     return render_template("edit_fd.html", fd=fd)






# @app.route('/financial_report')
# def financial_report():
#     conn = getfd()

#     # Summary totals
#     total_income = conn.execute(
#         "SELECT SUM(amount) FROM transactions WHERE type='credit'"
#     ).fetchone()[0] or 0

#     total_expenses = conn.execute(
#         "SELECT SUM(amount) FROM expenditures"
#     ).fetchone()[0] or 0

#     profit = total_income - total_expenses
#     balance = total_income - total_expenses  # You can adjust this if you have a different logic

#     # Breakdown by income category
#     income_by_category = conn.execute("""
#         SELECT category, SUM(amount) FROM transactions 
#         WHERE type='credit' 
#         GROUP BY category
#     """).fetchall()

#     # Breakdown by expense charge type
#     expenses_by_category = conn.execute("""
#         SELECT charge_type, SUM(amount) FROM expenditures 
#         GROUP BY charge_type
#     """).fetchall()

#     # Detailed expense records including acc_id and name
#     detailed_expenses = conn.execute("""
#         SELECT acc_id, name, charge_type, amount, description, created_at 
#         FROM expenditures 
#         ORDER BY created_at DESC
#     """).fetchall()

#     # Render financial report template
#     return render_template("financial_report.html",
#         income=total_income,
#         expenses=total_expenses,
#         profit=profit,
#         balance=balance,
#         income_by_category=dict(income_by_category),
#         expenses_by_category=dict(expenses_by_category),
#         expenses_list=detailed_expenses  # ✅ match template loop
#     )





@app.route("/customer_profile", methods=["GET", "POST"])
@login_required
def customer_profile():
    if request.method == "POST":
        query = request.form.get("query", "").strip()  # Safely get input

        if not query:
            flash("Please enter a valid search query!", "warning")
            return redirect("/search")

        conn = get_db_connection()

        # Search for the customer by name or account ID
        customer = conn.execute(""" 
            SELECT *
            FROM accounts 
            WHERE id LIKE ? OR full_name LIKE ?""", (f"%{query}%", f"%{query}%")).fetchone()

        if not customer:
            flash("Customer not found!", "danger")
            conn.close()
            return redirect("/search")

        # Convert customer data to a dictionary
        customer = dict(customer)
        customer["balance"] = float(customer.get("balance", 0.0))
        customer["share_fee"] = float(customer.get("share_fee", 0.0))
        customer["admin_fee"] = float(customer.get("admin_fee", 0.0))

        # Fetch and process deposits
        deposits = conn.execute(""" 
            SELECT amount, timestamp 
            FROM transactions 
            WHERE account_id = ? AND transaction_type = 'Deposit'""", (customer['id'],)).fetchall()
        deposits = [dict(row) for row in deposits]

        # Fetch and process withdrawals
        withdrawals = conn.execute(""" 
            SELECT amount, timestamp 
            FROM transactions 
            WHERE account_id = ? AND transaction_type = 'Withdrawal'""", (customer['id'],)).fetchall()
        withdrawals = [dict(row) for row in withdrawals]

        # Fetch and process loans
        loans = conn.execute(""" 
            SELECT loan_type, loan_amount, interest_rate, nominee_name, nominee_id, timestamp
            FROM loans 
            WHERE account_id = ?""", (customer['id'],)).fetchall()
        loans = [dict(row) for row in loans]

        # Fetch and process FD accounts
        fd_accounts = conn.execute(""" 
            SELECT fd_amount, interest_rate, maturity_date, total_amount, fd_id
            FROM fd_accounts 
            WHERE account_id = ?""", (customer['id'],)).fetchall()
        fd_accounts = [dict(row) for row in fd_accounts]

        conn.close()  # Ensure connection is closed before rendering

        return render_template("customer_profile.html", 
                               customer=customer, 
                               deposits=deposits, 
                               withdrawals=withdrawals, 
                               loans=loans, 
                               fd_accounts=fd_accounts)

    return render_template("customer_profile.html")




@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    results = None
    if request.method == "POST":
        query = request.form["query"]
        conn = get_db_connection()
        results = conn.execute("""
            SELECT id, full_name, phone, balance, account_type, address ,share_fee, admin_fee, timestamp
            FROM accounts 
            WHERE id LIKE ? OR full_name LIKE ? OR phone LIKE ?""",
            (f"%{query}%", f"%{query}%", f"%{query}%")).fetchall()
        conn.close()
    return render_template("search.html", results=results)



@app.route("/fd_holders")
@login_required
def fd_holders():
    conn = get_db_connection()
    query = """
        SELECT f.fd_id, 
               f.account_id, 
               f.fd_amount, 
               f.interest_rate, 
               f.interest_amount, 
               f.total_amount,
               f.fd_date,
               f.maturity_date, 
               a.full_name, 
               a.phone
        FROM fd_accounts f
        INNER JOIN accounts a ON f.account_id = a.id
    """
    results = conn.execute(query).fetchall()
    conn.close()
    return render_template("fd_holders.html", results=results)





    

@app.route('/mini_statement')
def mini_statement():
    conn = get_db_connection()
    stmt = conn.execute("SELECT * FROM transactions ORDER BY timestamp DESC LIMIT 10").fetchall()
    conn.close()
    return render_template("mini_statement.html", transactions=stmt)


@app.route("/edit/<string:table_id>/<int:record_id>", methods=["GET", "POST"])
@login_required
def edit_record(table_id, record_id):
    print(f"Table ID: {table_id}, Record ID: {record_id}")
    
    table_column_map = {
        "accounts": "id",
        "closed_accounts": "id",
        "loans": "id",
        "transactions": "id",
        "fd_accounts": "fd_id",
    }

    record_column = table_column_map.get(table_id)
    if not record_column:
        return "Invalid table", 400

    conn = get_db_connection()
    
    if request.method == "POST":
        updated_data = {}
        for key, value in request.form.items():
            updated_data[key] = float(value) if value.replace('.', '', 1).isdigit() else value

        set_clause = ', '.join([f"{key} = ?" for key in updated_data])
        values = list(updated_data.values()) + [record_id]

        try:
            conn.execute(f"UPDATE {table_id} SET {set_clause} WHERE {record_column} = ?", values)
            conn.commit()
        finally:
            conn.close()

        return redirect(url_for("generate_report"))

    else:
        try:
            record = conn.execute(f"SELECT * FROM {table_id} WHERE {record_column} = ?", (record_id,)).fetchone()
        finally:
            conn.close()

        if record:
            return render_template("edit_record.html", table_id=table_id, record=dict(record))
        else:
            return "Record not found", 404


@app.route("/close_account", methods=["GET", "POST"])
@login_required
def close_account():
    if request.method == "POST":
        account_id = request.form["account_id"]  # Assuming you're sending account ID from the form

        conn = get_db_connection()
        account = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()

        if account:
            conn.execute("""
                INSERT INTO closed_accounts (account_id, full_name, phone, dob, address, account_type, balance)
                SELECT id, full_name, phone, dob, address, account_type, balance
                FROM accounts
                WHERE id = ?
            """, (account_id,))
            conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
            conn.commit()
            flash("Account closed successfully!")
        else:
            flash("Account not found!")

        conn.close()
        return redirect("/admin_dashboard")

    return render_template("close_account.html")




# Search endpoint for the AJAX search
@app.route("/search_accounts")

def search_accounts():
    query = request.args.get("q", "").strip()
    
    if len(query) < 2:
        return jsonify([])
    
    try:
        conn = get_db_connection()
        results = conn.execute(
            """SELECT id, account_number, full_name, account_type, balance 
               FROM accounts 
               WHERE account_number LIKE ? OR full_name LIKE ?
               LIMIT 10""",
            (f"%{query}%", f"%{query}%")
        ).fetchall()
        
        return jsonify([dict(row) for row in results])
        
    except sqlite3.Error as e:
        print(f"Search error: {e}")
        return jsonify([])
        
    finally:
        if conn:
            conn.close()

# Function to fetch data and save as Excel
def export_all_tables_to_excel():
    try:
        # Connect to the database
        conn = sqlite3.connect("db/bank.db")
        print("Connected to the database successfully.")  # Debugging

        # List of tables to export
        tables = [
            "accounts",
            "transactions",
            "loans",
            "fd_accounts",
            "emi_payments",
            "closed_accounts"
        ]

        # Export each table to a separate Excel file
        for table in tables:
            query = f"SELECT * FROM {table}"
            df = pd.read_sql(query, conn)

            # Save the data to an Excel file
            file_path = f"{table}_data.xlsx"
            df.to_excel(file_path, index=False)
            print(f"Excel file generated for {table}: {file_path}")  # Debugging

        conn.close()
        return True  # Success

    except Exception as e:
        print(f"Error exporting data to Excel: {e}")  # Debugging
        return False  # Failure

# Route to trigger the download of all tables as Excel files

@app.route("/download_all_tables")

def download_all_tables():
    if export_all_tables_to_excel():
        zip_path = "all_tables.zip"
        with zipfile.ZipFile(zip_path, "w") as zipf:
            for table in ["accounts", "transactions", "loans", "fd_accounts", "emi_payments", "closed_accounts"]:
                file_path = f"{table}_data.xlsx"
                if os.path.exists(file_path):
                    zipf.write(file_path, os.path.basename(file_path))
                    os.remove(file_path)

        # Corrected: Remove 'filename' argument when sending an existing file
        return send_file(zip_path, as_attachment=True, mimetype="application/zip")  # Changed here
    else:
        return "Failed to generate Excel files.", 500







# from datetime import timedelta





@app.route("/search_loans")
def search_loans():
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return jsonify([])
    
    conn = get_db_connection()
    try:
        results = conn.execute("""
            SELECT loans.id, accounts.full_name, loans.loan_type, 
                   loans.loan_amount, loans.remaining_balance
            FROM loans
            JOIN accounts ON loans.account_id = accounts.id
            WHERE accounts.full_name LIKE ? OR loans.id LIKE ?
            LIMIT 10
        """, (f"%{query}%", f"%{query}%")).fetchall()
        
        return jsonify([dict(row) for row in results])
    finally:
        conn.close()




from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime, timedelta


@app.route('/banking-dashboard')
def banking_dashboard():
    return render_template('banking_dashboard.html')



@app.route('/premium-banking')
def premium_banking_component():
    return render_template('premium_banking.html')

# Main Page with Download Button
@app.route("/index")
def index():
    return render_template("index.html")

@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "-1"
    return response





@app.route('/process_deposit', methods=["POST"])
def process_deposit():
    account_id = request.form["account_id"]
    amount = float(request.form["amount"])
    note = request.form.get("note", "")
    
    conn = get_db_connection()
    conn.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, account_id))
    conn.execute("INSERT INTO transactions (account_id, transaction_type, amount, note) VALUES (?, 'Deposit', ?, ?)", (account_id, amount, note))
    conn.commit()
    conn.close()

    flash("Deposit successful", "success")
    return redirect(url_for("transactions"))

@app.route('/process_withdrawal', methods=["POST"])
def process_withdrawal():
    account_id = request.form["account_id"]
    amount = float(request.form["amount"])
    note = request.form.get("note", "")

    conn = get_db_connection()
    # Optionally: check balance before withdrawing
    account = conn.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,)).fetchone()
    if account and account["balance"] >= amount:
        conn.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, account_id))
        conn.execute("INSERT INTO transactions (account_id, transaction_type, amount, note) VALUES (?, 'Withdrawal', ?, ?)", (account_id, amount, note))
        conn.commit()
        flash("Withdrawal successful", "success")
    else:
        flash("Insufficient balance", "danger")
    conn.close()
    return redirect(url_for("transactions"))

@app.route('/process_transfer', methods=["POST"])
def process_transfer():
    from_account = int(request.form["from_account"])
    to_account = int(request.form["to_account"])
    amount = float(request.form["amount"])
    note = request.form.get("note", "")

    if from_account == to_account:
        flash("Cannot transfer to the same account!", "warning")
        return redirect(url_for("transactions"))

    conn = get_db_connection()
    balance = conn.execute("SELECT balance FROM accounts WHERE id = ?", (from_account,)).fetchone()
    if balance and balance["balance"] >= amount:
        # Debit from sender
        conn.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, from_account))
        conn.execute("INSERT INTO transactions (account_id, transaction_type, amount, note) VALUES (?, 'Transfer Out', ?, ?)", (from_account, amount, note))

        # Credit to receiver
        conn.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, to_account))
        conn.execute("INSERT INTO transactions (account_id, transaction_type, amount, note) VALUES (?, 'Transfer In', ?, ?)", (to_account, amount, note))

        conn.commit()
        flash("Transfer successful", "success")
    else:
        flash("Insufficient balance", "danger")
    conn.close()
    return redirect(url_for("transactions"))

@app.route('/transactions')
def transactions():
    conn = get_db_connection()
    accounts = conn.execute("SELECT id, account_number, full_name AS customer_name, balance FROM accounts").fetchall()
    txns = conn.execute("""
        SELECT t.*, a.account_number 
        FROM transactions t 
        JOIN accounts a ON a.id = t.account_id 
        ORDER BY t.timestamp DESC LIMIT 20
    """).fetchall()
    conn.close()
    return render_template("transaction.html", accounts=accounts, transactions=txns)




# @app.route('/expenditure')
# @login_required
# def expenditure():
#     conn = get_db_connection()
#     conn.row_factory = sqlite3.Row  # Ensure column names work for dictionary access
#     cur = conn.cursor()

#     try:
#         # 1. Totals
#         cur.execute("SELECT SUM(amount) FROM income")
#         total_income = cur.fetchone()[0] or 0

#         cur.execute("SELECT SUM(amount) FROM expenditures")
#         total_expenses = cur.fetchone()[0] or 0

#         profit = total_income - total_expenses
#         loss = total_expenses - total_income if total_expenses > total_income else 0
#         savings = profit if profit > 0 else 0

#         # 2. Bank balance (basic logic here)
#         bank_balance = savings

#         # 3. Other Financials
#         cur.execute("SELECT SUM(share_amount) FROM shares")
#         total_shares = cur.fetchone()[0] or 0

#         cur.execute("SELECT SUM(amount) FROM loans")
#         total_loan_amount = cur.fetchone()[0] or 0

#         cur.execute("SELECT SUM(paid_amount) FROM loan_repayments")
#         recovery_amount = cur.fetchone()[0] or 0

#         cur.execute("SELECT SUM(amount) FROM fixed_deposits")
#         fd_amount = cur.fetchone()[0] or 0

#         cur.execute("SELECT SUM(amount) FROM transactions WHERE DATE(created_at) = DATE('now', 'localtime')")
#         today_transaction_amount = cur.fetchone()[0] or 0

#         # 4. Income by category
#         cur.execute("""
#             SELECT c.name AS category, SUM(i.amount) AS total
#             FROM income i
#             JOIN income_categories c ON i.category_id = c.id
#             GROUP BY c.name
#         """)
#         income_by_category = {row["category"]: row["total"] for row in cur.fetchall()}

#         # 5. Expenses by category
#         cur.execute("""
#             SELECT c.name AS category, SUM(e.amount) AS total
#             FROM expenditures e
#             JOIN expense_categories c ON e.category_id = c.id
#             GROUP BY c.name
#         """)
#         expenses_by_category = {row["category"]: row["total"] for row in cur.fetchall()}

#     except Exception as e:
#         flash(f"Error fetching data: {e}", "danger")
#         return redirect(url_for("admin_dashboard"))
#     finally:
#         conn.close()

#     # ✅ Add the return statement here!
#     return render_template(
#         'expenditure.html',
#         income=income_by_category,
#         expenses=expenses_by_category,
#         income_total=total_income,
#         expenditure_total=total_expenses,
#         profit=profit,
#         loss=loss,
#         savings=savings,
#         balance=bank_balance,
#         total_shares=total_shares,
#         loan_amount=total_loan_amount,
#         recovery_amount=recovery_amount,
#         fd_amount=fd_amount,
#         today_transaction=today_transaction_amount
#     )
    



# @app.route('/expenditure')
# @login_required
# def expenditure():
#     conn = get_db_connection()
#     conn.row_factory = sqlite3.Row
#     cur = conn.cursor()

#     try:
#         # Totals
#         cur.execute("SELECT SUM(amount) FROM income")
#         total_income = cur.fetchone()[0] or 0

#         cur.execute("SELECT SUM(amount) FROM expenditures")
#         total_expenses = cur.fetchone()[0] or 0

#         profit = total_income - total_expenses
#         savings = profit if profit > 0 else 0
#         bank_balance = savings

#         # Additional Financials
#         cur.execute("SELECT SUM(share_amount) FROM shares")
#         total_shares = cur.fetchone()[0] or 0

#         cur.execute("SELECT SUM(amount) FROM loans")
#         total_loan_amount = cur.fetchone()[0] or 0

#         cur.execute("SELECT SUM(paid_amount) FROM loan_repayments")
#         recovery_amount = cur.fetchone()[0] or 0

#         cur.execute("SELECT SUM(amount) FROM fixed_deposits")
#         fd_amount = cur.fetchone()[0] or 0

#         cur.execute("SELECT SUM(amount) FROM transactions WHERE DATE(created_at) = DATE('now', 'localtime')")
#         today_transaction_amount = cur.fetchone()[0] or 0

#         # Income by category (includes file charges if categorized correctly)
#         cur.execute("""
#             SELECT c.name AS category, SUM(i.amount) AS total
#             FROM income i
#             JOIN income_categories c ON i.category_id = c.id
#             GROUP BY c.name
#         """)
#         income_by_category = {row["category"]: row["total"] for row in cur.fetchall()}

#         # Expense by category
#         cur.execute("""
#             SELECT c.name AS category, SUM(e.amount) AS total
#             FROM expenditures e
#             JOIN expense_categories c ON e.category_id = c.id
#             GROUP BY c.name
#         """)
#         expenses_by_category = {row["category"]: row["total"] for row in cur.fetchall()}

#     except Exception as e:
#         flash(f"Error: {e}", "danger")
#         return redirect(url_for("admin_dashboard"))
#     finally:
#         conn.close()

#     return render_template(
#         'expenditure.html',
#         income=income_by_category,
#         expenses=expenses_by_category,
#         income_total=total_income,
#         expenditure_total=total_expenses,
#         profit=profit,
#         loss=max(0, total_expenses - total_income),
#         savings=savings,
#         balance=bank_balance,
#         total_shares=total_shares,
#         loan_amount=total_loan_amount,
#         recovery_amount=recovery_amount,
#         fd_amount=fd_amount,
#         today_transaction=today_transaction_amount
#     )

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
@app.route('/expenditure')
@login_required
def expenditure():
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        # Real Income Sources
        cur.execute("SELECT SUM(admin_fee) FROM accounts")
        admin_fee = cur.fetchone()[0] or 0

        cur.execute("SELECT SUM(share_fee) FROM accounts")
        share_fee = cur.fetchone()[0] or 0

        cur.execute("SELECT SUM(file_charge_fee) FROM accounts")
        file_charge_fee = cur.fetchone()[0] or 0

        cur.execute("SELECT SUM(paid_amount) FROM loan_repayments")
        loan_interest = cur.fetchone()[0] or 0

        # Income by category
        income_by_category = {
            "Admin Fee": admin_fee,
            "Share Fee": share_fee,
            "Loan File Charges": file_charge_fee,
            "Loan Interest (Recovered)": loan_interest
        }

        total_income = sum(income_by_category.values())

        # Expenses
        cur.execute("SELECT SUM(amount) FROM expenditures")
        total_expenses = cur.fetchone()[0] or 0

        # Profit/Loss/Balance
        profit = total_income - total_expenses
        savings = max(0, profit)
        balance = savings

        # Extra Info
        cur.execute("SELECT SUM(share_amount) FROM shares")
        total_shares = cur.fetchone()[0] or 0

        cur.execute("SELECT SUM(amount) FROM loans")
        total_loan_amount = cur.fetchone()[0] or 0

        cur.execute("SELECT SUM(paid_amount) FROM loan_repayments")
        recovery_amount = cur.fetchone()[0] or 0

        cur.execute("SELECT SUM(amount) FROM fixed_deposits")
        fd_amount = cur.fetchone()[0] or 0

        cur.execute("SELECT SUM(amount) FROM transactions WHERE DATE(created_at) = DATE('now', 'localtime')")
        today_transaction_amount = cur.fetchone()[0] or 0

        # Expense by category
        cur.execute("""
            SELECT c.name AS category, SUM(e.amount) AS total
            FROM expenditures e
            JOIN expense_categories c ON e.category_id = c.id
            GROUP BY c.name
        """)
        expenses_by_category = {row["category"]: row["total"] for row in cur.fetchall()}

    except Exception as e:
        flash(f"Error: {e}", "danger")
        return redirect(url_for("admin_dashboard"))
    finally:
        conn.close()

    return render_template(
        'expenditure.html',
        income=income_by_category,
        expenses=expenses_by_category,
        income_total=total_income,
        expenditure_total=total_expenses,
        profit=profit,
        loss=max(0, total_expenses - total_income),
        savings=savings,
        balance=balance,
        total_shares=total_shares,
        loan_amount=total_loan_amount,
        recovery_amount=recovery_amount,
        fd_amount=fd_amount,
        today_transaction=today_transaction_amount
    )

    
@app.route('/fee-details', methods=['GET'])
@login_required
def fee_details():
    conn = get_db_connection()
    filters = []
    params = []

    # Get query params
    start = request.args.get('start_date')
    end = request.args.get('end_date')
    month = request.args.get('month')
    year = request.args.get('year')

    # Base query: Join loans and accounts
    query = """
        SELECT 
            a.id,
            a.account_number,
            a.full_name,
            IFNULL(a.file_charge_fee, 0) AS account_file_charge,
            IFNULL(SUM(l.file_charge), 0) AS loan_file_charge,
            IFNULL(a.admin_fee, 0) AS admin_fee,
            IFNULL(a.share_fee, 0) AS share_fee
        FROM accounts a
        LEFT JOIN loans l ON l.account_id = a.id
    """

    if start and end:
        filters.append("a.timestamp BETWEEN ? AND ?")
        params.extend([start, end])
    elif month:
        filters.append("strftime('%m', a.timestamp) = ?")
        params.append(f"{int(month):02}")
    if year:
        filters.append("strftime('%Y', a.timestamp) = ?")
        params.append(year)

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " GROUP BY a.id"

    fees = conn.execute(query, params).fetchall()
    conn.close()

    return render_template("fee_details.html", fees=fees, current_year=datetime.now().year)


# @app.route('/add-income', methods=['GET', 'POST'])
# def add_income():
#     if request.method == 'POST':
#         amount = request.form['amount']
#         category = request.form['category']
#         description = request.form['description']
#         with sqlite3.connect("your_database.db") as conn:
#             cur = conn.cursor()
#             cur.execute("INSERT INTO incomes (amount, category, description, created_at) VALUES (?, ?, ?, datetime('now'))",
#                         (amount, category, description))
#             conn.commit()
#         return redirect(url_for('dashboard'))  # or your home view

#     categories = get_income_categories()  # define this function to load income category names
#     return render_template('add_income.html', income_categories=categories)




@app.route('/add_expenditure', methods=['GET', 'POST'])
@login_required
def add_expenditure():
    conn = get_db_connection()
    if request.method == 'POST':
        amount = request.form['amount']
        charge_type = request.form['charge_type']
        description = request.form.get('description')
        recorded_by = "ADMIN"

        category = conn.execute(
            "SELECT id FROM expense_categories WHERE name = ?", 
            (charge_type,)
        ).fetchone()
        if not category:
            flash("Invalid category.", "danger")
            return redirect(url_for('add_expenditure'))

        category_id = category['id']

        conn.execute("""
            INSERT INTO expenditures (amount, category_id, description, recorded_by)
            VALUES (?, ?, ?, ?)
        """, (amount, category_id, description, recorded_by))
        conn.commit()
        conn.close()

        flash("Expenditure added successfully!", "success")
        return redirect(url_for('expenditure'))

    categories = conn.execute("SELECT name FROM expense_categories").fetchall()
    conn.close()
    return render_template("add_expenditure.html", categories=[c["name"] for c in categories])





@app.route('/expenditure_history')
@login_required
def expenditure_history():
    date_filter = request.args.get('date')
    charge_type_filter = request.args.get('charge_type')

    conn = get_db_connection()
    cur = conn.cursor()


    
    
    query = """
        SELECT e.id, e.amount, e.description, e.recorded_by, e.recorded_at,
               c.name AS charge_type
        FROM expenditures e
        JOIN expense_categories c ON e.category_id = c.id
        WHERE 1=1
        
        
        
        
    """
    params = []

    if date_filter:
        query += " AND DATE(e.recorded_at) = ?"
        params.append(date_filter)

    if charge_type_filter:
        query += " AND c.name = ?"
        params.append(charge_type_filter)

    query += " ORDER BY e.recorded_at DESC"

    cur.execute(query, params)
    expenses = cur.fetchall()

    # Get all charge types for the dropdown
    cur.execute("SELECT DISTINCT name FROM expense_categories")
    charge_types = [row["name"] for row in cur.fetchall()]

    conn.close()

    return render_template(
        "expenditure_history.html",
        expenses_list=expenses,
        charge_types=charge_types,
        selected_date=date_filter,
        selected_charge_type=charge_type_filter
    )


# @app.route('/fee-details')
# def view_fee_details():
#     conn = get_db_connection()
#     accounts = conn.execute("""
#         SELECT id, account_number, full_name, admin_fee, file_charge_fee, share_fee
#         FROM accounts
#     """).fetchall()
#     conn.close()
#     return render_template("fee_details.html", accounts=accounts)
# from werkzeug.security import generate_password_hash, check_password_hash



@app.route('/fee-details')
def view_fee_details():
    conn = get_db_connection()
    fees = conn.execute("""
        SELECT id, account_number, full_name, admin_fee, file_charge_fee, share_fee
        FROM accounts
    """).fetchall()
    conn.close()
    return render_template("fee_details.html", fees=fees)



@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if request.method == "POST":
        username = request.form["username"]
        old_password = request.form["old_password"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        if new_password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for("change_password"))

        conn = get_db_connection()
        admin = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()

        if not admin:
            flash("Username not found!", "danger")
            conn.close()
            return redirect(url_for("change_password"))

        if not check_password_hash(admin["password"], old_password):
            flash("Old password is incorrect!", "danger")
            conn.close()
            return redirect(url_for("change_password"))

        # Update password
        hashed_password = generate_password_hash(new_password)
        conn.execute("UPDATE admins SET password = ? WHERE username = ?", (hashed_password, username))
        conn.commit()
        conn.close()

        flash("Password changed successfully!", "success")
        return redirect(url_for("login"))

    return render_template("change_password.html")







# if __name__ == "__main__":
#     app.run(host="127.0.0.1", port=443, ssl_context=('cert.pem', 'key.pem'))



if __name__ == '__main__':
    #webview.create_window('Desktop App', 'http://127.0.0.1:5000')
    app.run(host= "myapp.local", port=5000, debug=True, use_reloader=False)