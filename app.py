from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
import sqlite3
import random
import string
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = "vita-secret-123"
ADMIN_PASSWORD = "vita123"

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect('vita.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS licenses 
                 (key TEXT PRIMARY KEY, client_name TEXT, account TEXT, product TEXT, expiry TEXT, status TEXT)''')
    conn.commit()
    conn.close()

init_db()

def generate_key_code():
    return 'VITA-ALL-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# --- HTML Templates (Clean VitaTraders) ---
HOME_HTML = """
<h1 style="text-align:center; font-family:Arial;">VITA TRADERS 🔥</h1>
<p style="text-align:center;">EA for BTC | XAUUSD | US30 | US100 | GER30 | NAS100</p>
<p style="text-align:center;"><a href="/admin">Admin Login</a></p>
<p style="text-align:center; color:green;">Website is LIVE!</p>
"""

ADMIN_LOGIN_HTML = """
<h2>VitaTraders Admin Login</h2>
<form method="post">
<input type="password" name="password" placeholder="Password">
<button type="submit">Login</button>
</form>
"""

ADMIN_DASH_HTML = """
<h2>VitaTraders Dashboard - Manage Licenses</h2>
<p><a href="/logout">Logout</a></p>
<h3>Generate New License</h3>
<form method="post" action="/admin/generate">
Client Name: <input name="client_name" required><br><br>
MT5 Account (leave blank = auto-bind): <input name="account"><br><br>
Product: 
<select name="product">
<option>VITA-ALL</option>
<option>BTC</option>
<option>XAUUSD</option>
<option>US30</option>
</select><br><br>
Expiry: 
<select name="expiry">
<option value="lifetime">Lifetime</option>
<option value="30">30 Days</option>
<option value="7">7 Days</option>
</select><br><br>
<button type="submit">Generate Key</button>
</form>
<hr>
<h3>All Licenses</h3>
<table border="1" cellpadding="10">
<tr><th>Key</th><th>Client</th><th>Account</th><th>Product</th><th>Expiry</th><th>Status</th><th>Action</th></tr>
{% for row in licenses %}
<tr>
<td>{{ row[0] }}</td><td>{{ row[1] }}</td><td>{{ row[2] }}</td><td>{{ row[3] }}</td><td>{{ row[4] }}</td><td>{{ row[5] }}</td>
<td><a href="/admin/delete/{{ row[0] }}">DELETE (Block Client)</a></td>
</tr>
{% endfor %}
</table>
"""

@app.route('/')
def home():
    return HOME_HTML

# --- API FOR MT5 EA ---
@app.route('/api/check')
def check_license():
    key = request.args.get('key', '')
    account = request.args.get('account', '')
    
    conn = sqlite3.connect('vita.db')
    c = conn.cursor()
    c.execute("SELECT * FROM licenses WHERE key=?", (key,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        return jsonify({"valid": False, "message": "Invalid License Key"})
    
    # row = key, client_name, account, product, expiry, status
    db_key, client_name, db_account, product, expiry, status = row

    if status != "active":
        conn.close()
        return jsonify({"valid": False, "message": "License Deactivated by Admin"})

    # Auto-bind account on first use
    if not db_account or db_account == "" or db_account == "None":
        c.execute("UPDATE licenses SET account=? WHERE key=?", (account, key))
        conn.commit()
    elif str(db_account) != str(account) and str(account) != "":
        conn.close()
        return jsonify({"valid": False, "message": f"Key bound to other account {db_account}"})

    # Check expiry
    if expiry != "lifetime":
        try:
            exp_date = datetime.strptime(expiry, "%Y-%m-%d")
            if datetime.now() > exp_date:
                conn.close()
                return jsonify({"valid": False, "message": "License Expired"})
        except:
            pass

    conn.close()
    return jsonify({"valid": True, "message": "License Active", "client": client_name, "product": product})

# --- ADMIN ---
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin_dash'))
        else:
            return "Wrong password! <a href='/admin'>Try again</a>"
    return ADMIN_LOGIN_HTML

@app.route('/admin/dashboard')
def admin_dash():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    conn = sqlite3.connect('vita.db')
    c = conn.cursor()
    c.execute("SELECT * FROM licenses")
    licenses = c.fetchall()
    conn.close()
    return render_template_string(ADMIN_DASH_HTML, licenses=licenses)

@app.route('/admin/generate', methods=['POST'])
def admin_generate():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    client_name = request.form.get('client_name')
    account = request.form.get('account')
    product = request.form.get('product')
    expiry_choice = request.form.get('expiry')

    if expiry_choice == "lifetime":
        expiry = "lifetime"
    else:
        expiry = (datetime.now() + timedelta(days=int(expiry_choice))).strftime("%Y-%m-%d")

    new_key = generate_key_code()

    conn = sqlite3.connect('vita.db')
    c = conn.cursor()
    c.execute("INSERT INTO licenses VALUES (?,?,?,?,?,?)", (new_key, client_name, account, product, expiry, "active"))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dash'))

@app.route('/admin/delete/<key>')
def admin_delete(key):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    conn = sqlite3.connect('vita.db')
    c = conn.cursor()
    c.execute("DELETE FROM licenses WHERE key=?", (key,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dash'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
