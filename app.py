from flask import Flask, render_template, request, redirect, session, make_response, jsonify
import sqlite3
import csv

app = Flask(__name__)
app.secret_key = "secret123"

# ---------- DATABASE ---------- #

def connect():
    return sqlite3.connect('database.db')

def init_db():
    conn = connect()
    cursor = conn.cursor()

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
        if request.form['username'] == "admin" and request.form['password'] == "1234":
            session['user'] = "admin"
            return redirect('/')
        return "Invalid Credentials"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

# ---------- HOME + SEARCH ---------- #

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user' not in session:
        return redirect('/login')

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
def add():
    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':
        name = request.form['name']
        s1, s2, s3 = int(request.form['s1']), int(request.form['s2']), int(request.form['s3'])

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
def update(id):
    if 'user' not in session:
        return redirect('/login')

    conn = connect()
    cursor = conn.cursor()

    if request.method == 'POST':
        s1, s2, s3 = int(request.form['s1']), int(request.form['s2']), int(request.form['s3'])

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
def delete(id):
    if 'user' not in session:
        return redirect('/login')

    conn = connect()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect('/')

# ---------- EXPORT CSV ---------- #

import csv
import io
from flask import Response

@app.route('/export')
def export():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students")
    data = cursor.fetchall()
    conn.close()

    # Create file in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Add header
    writer.writerow(['ID', 'Name', 'Subject1', 'Subject2', 'Subject3', 'Total', 'Percentage', 'Grade'])

    # Add data
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

# ---------- TOPPER ---------- #

@app.route('/topper')
def topper():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students ORDER BY percentage DESC LIMIT 1")
    t = cursor.fetchone()
    conn.close()

    return render_template('topper.html', topper=t)

# ---------- RUN ---------- #

if __name__ == "__main__":
    init_db()
    if __name__ == "__main__":
        app.run()