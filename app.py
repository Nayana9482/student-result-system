from flask import Flask, render_template, request, redirect, session, jsonify, Response
import sqlite3
import bcrypt
import csv
import io
from functools import wraps

app = Flask(__name__)
app.secret_key = "my_super_secure_key_2026"

# ---------- DATABASE ---------- #

def connect():
    return sqlite3.connect('database.db')

def init_db():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password BLOB,
        role TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        subject1 INTEGER,
        subject2 INTEGER,
        subject3 INTEGER,
        total INTEGER,
        percentage REAL,
        grade TEXT
    )
    """)

    conn.commit()
    conn.close()

# ---------- CREATE ADMIN ---------- #

def create_admin():
    conn = connect()
    cursor = conn.cursor()

    password = bcrypt.hashpw("Admin@123".encode(), bcrypt.gensalt())

    try:
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ("admin", password, "admin")
        )
        conn.commit()
    except:
        pass

    conn.close()

# ---------- DECORATORS ---------- #

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user' not in session or session.get('role') != 'admin':
            return "Access Denied"
        return f(*args, **kwargs)
    return wrapper

# ---------- LOGIC ---------- #

def calculate_grade(p):
    if p >= 90:
        return "A"
    elif p >= 75:
        return "B"
    elif p >= 50:
        return "C"
    else:
        return "Fail"

# ---------- AUTH ---------- #

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cursor.fetchone()
        conn.close()

        # ✅ Correct bcrypt check (NO .encode() on DB password)
        if user and bcrypt.checkpw(password.encode(), user[2]):
            session['user'] = user[1]
            session['role'] = user[3]
            return redirect('/')
        else:
            return "Invalid credentials"

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ---------- REGISTER ---------- #

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

        conn = connect()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                (username, hashed, "student")
            )
            conn.commit()
            conn.close()
            return redirect('/login')
        except:
            conn.close()
            return "User already exists"

    return render_template('register.html')

# ---------- HOME + SEARCH ---------- #

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    conn = connect()
    cursor = conn.cursor()

    if request.method == 'POST':
        keyword = request.form['search']
        cursor.execute("SELECT * FROM students WHERE name LIKE ?", ('%' + keyword + '%',))
    else:
        cursor.execute("SELECT * FROM students")

    students = cursor.fetchall()
    conn.close()

    return render_template('index.html', students=students)

# ---------- ADD ---------- #

@app.route('/add', methods=['GET', 'POST'])
@admin_required
def add():
    if request.method == 'POST':
        name = request.form['name']
        s1 = int(request.form['s1'])
        s2 = int(request.form['s2'])
        s3 = int(request.form['s3'])

        total = s1 + s2 + s3
        percentage = total / 3
        grade = calculate_grade(percentage)

        conn = connect()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO students (name, subject1, subject2, subject3, total, percentage, grade)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, s1, s2, s3, total, percentage, grade))

        conn.commit()
        conn.close()

        return redirect('/')

    return render_template('add.html')

# ---------- UPDATE ---------- #

@app.route('/update/<int:id>', methods=['GET', 'POST'])
@admin_required
def update(id):
    conn = connect()
    cursor = conn.cursor()

    if request.method == 'POST':
        s1 = int(request.form['s1'])
        s2 = int(request.form['s2'])
        s3 = int(request.form['s3'])

        total = s1 + s2 + s3
        percentage = total / 3
        grade = calculate_grade(percentage)

        cursor.execute("""
        UPDATE students
        SET subject1=?, subject2=?, subject3=?, total=?, percentage=?, grade=?
        WHERE id=?
        """, (s1, s2, s3, total, percentage, grade, id))

        conn.commit()
        conn.close()
        return redirect('/')

    cursor.execute("SELECT * FROM students WHERE id=?", (id,))
    student = cursor.fetchone()
    conn.close()

    return render_template('update.html', student=student)

# ---------- DELETE ---------- #

@app.route('/delete/<int:id>')
@admin_required
def delete(id):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect('/')

# ---------- EXPORT CSV ---------- #

@app.route('/export')
@login_required
def export():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students")
    data = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(['ID', 'Name', 'Subject1', 'Subject2', 'Subject3', 'Total', 'Percentage', 'Grade'])

    for row in data:
        writer.writerow(row)

    output.seek(0)

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=students.csv"}
    )

# ---------- CHART DATA ---------- #

@app.route('/chart-data')
@login_required
def chart_data():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT name, percentage FROM students")
    data = cursor.fetchall()
    conn.close()

    return jsonify({
        "names": [x[0] for x in data],
        "percentages": [x[1] for x in data]
    })

# ---------- DASHBOARD ---------- #

@app.route('/dashboard')
@login_required
def dashboard():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("SELECT name, percentage, subject1, subject2, subject3 FROM students")
    data = cursor.fetchall()

    cursor.execute("SELECT name, percentage FROM students ORDER BY percentage DESC LIMIT 1")
    topper = cursor.fetchone()

    conn.close()

    return render_template("dashboard.html", data=data, topper=topper)

# ---------- RUN ---------- #

if __name__ == "__main__":
    init_db()
    create_admin()
    app.run(debug=True)