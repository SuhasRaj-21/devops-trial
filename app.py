import os
import sqlite3
import csv
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify

import shutil

app = Flask(__name__)
app.secret_key = 'super_secret_key_attendance_system'

# On Vercel, the filesystem is read-only. We copy the sqlite database to /tmp to allow writes.
if os.environ.get('VERCEL') or os.environ.get('NOW_REGION'):
    DB_FILE = '/tmp/attendance.db'
    if not os.path.exists(DB_FILE):
        if os.path.exists('attendance.db'):
            shutil.copy('attendance.db', DB_FILE)
else:
    DB_FILE = 'attendance.db'


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    c = conn.cursor()

    # Create users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')

    # Create students table
    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            usn TEXT NOT NULL UNIQUE,
            department TEXT NOT NULL
        )
    ''')

    # Create attendance table
    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students (id)
        )
    ''')

    # Default admin
    c.execute('SELECT * FROM users WHERE username = ?', ('admin',))

    if not c.fetchone():
        c.execute(
            'INSERT INTO users (username, password) VALUES (?, ?)',
            ('admin', 'admin123')
        )

    # Sample students
    c.execute('SELECT COUNT(*) FROM students')

    if c.fetchone()[0] == 0:
        sample_students = [
            ('John Doe', '1USN001', 'Computer Science'),
            ('Jane Smith', '1USN002', 'Information Science'),
            ('Alice Johnson', '1USN003', 'Electronics'),
            ('Bob Brown', '1USN004', 'Mechanical')
        ]

        c.executemany(
            'INSERT INTO students (student_name, usn, department) VALUES (?, ?, ?)',
            sample_students
        )

    conn.commit()
    conn.close()


# Create exports folder (use /tmp on Vercel)
EXPORT_DIR = '/tmp/exports' if (os.environ.get('VERCEL') or os.environ.get('NOW_REGION')) else 'exports'
if not os.path.exists(EXPORT_DIR):
    os.makedirs(EXPORT_DIR)

# Initialize DB
init_db()


# Login decorator
def login_required(f):
    @wraps(f)

    def decorated_function(*args, **kwargs):

        if 'logged_in' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login'))

        return f(*args, **kwargs)

    return decorated_function


@app.route('/')
def index():

    if 'logged_in' in session:
        return redirect(url_for('dashboard'))

    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()

        user = conn.execute(
            'SELECT * FROM users WHERE username = ? AND password = ?',
            (username, password)
        ).fetchone()

        conn.close()

        if user:
            session['logged_in'] = True
            session['username'] = username

            flash('Login successful!', 'success')

            return redirect(url_for('dashboard'))

        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()

    flash('You have been logged out.', 'info')

    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():

    conn = get_db_connection()

    students_count = conn.execute(
        'SELECT COUNT(*) FROM students'
    ).fetchone()[0]

    today = datetime.now().strftime('%Y-%m-%d')

    present_count = conn.execute(
        'SELECT COUNT(*) FROM attendance WHERE date = ? AND status = "Present"',
        (today,)
    ).fetchone()[0]

    absent_count = conn.execute(
        'SELECT COUNT(*) FROM attendance WHERE date = ? AND status = "Absent"',
        (today,)
    ).fetchone()[0]

    conn.close()

    return render_template(
        'dashboard.html',
        students_count=students_count,
        present_count=present_count,
        absent_count=absent_count,
        today=today
    )


@app.route('/students', methods=['GET', 'POST'])
@login_required
def students():

    conn = get_db_connection()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            name = request.form['student_name']
            usn = request.form['usn']
            dept = request.form['department']
            try:
                conn.execute(
                    'INSERT INTO students (student_name, usn, department) VALUES (?, ?, ?)',
                    (name, usn, dept)
                )
                conn.commit()
                flash('Student added successfully!', 'success')
            except sqlite3.IntegrityError:
                flash('USN already exists!', 'danger')

        elif action == 'edit':
            student_id = request.form['student_id']
            name = request.form['student_name']
            usn = request.form['usn']
            dept = request.form['department']
            try:
                conn.execute(
                    'UPDATE students SET student_name=?, usn=?, department=? WHERE id=?',
                    (name, usn, dept, student_id)
                )
                conn.commit()
                flash('Student updated successfully!', 'success')
            except sqlite3.IntegrityError:
                flash('USN already exists!', 'danger')

        elif action == 'delete':
            student_id = request.form['student_id']
            conn.execute('DELETE FROM attendance WHERE student_id=?', (student_id,))
            conn.execute('DELETE FROM students WHERE id=?', (student_id,))
            conn.commit()
            flash('Student deleted successfully!', 'success')

        conn.close()
        return redirect(url_for('students'))

    search = request.args.get('search', '')
    if search:
        students = conn.execute(
            'SELECT * FROM students WHERE student_name LIKE ? OR usn LIKE ? OR department LIKE ?',
            (f'%{search}%', f'%{search}%', f'%{search}%')
        ).fetchall()
    else:
        students = conn.execute(
            'SELECT * FROM students'
        ).fetchall()

    conn.close()

    return render_template(
        'students.html',
        students=students,
        search=search
    )


@app.route('/attendance', methods=['GET', 'POST'])
@login_required
def attendance():

    conn = get_db_connection()
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))

    if request.method == 'POST':
        selected_date = request.form.get('date')

        # Get all students
        students = conn.execute('SELECT id FROM students').fetchall()

        for student in students:
            student_id = student['id']
            status = request.form.get(f'status_{student_id}')

            if status:
                # Check if record exists
                existing = conn.execute(
                    'SELECT id FROM attendance WHERE student_id=? AND date=?',
                    (student_id, selected_date)
                ).fetchone()

                if existing:
                    conn.execute(
                        'UPDATE attendance SET status=? WHERE id=?',
                        (status, existing['id'])
                    )
                else:
                    conn.execute(
                        'INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)',
                        (student_id, selected_date, status)
                    )

        conn.commit()
        conn.close()
        flash(f'Attendance marked for {selected_date} successfully!', 'success')
        return redirect(url_for('attendance', date=selected_date))

    # Get students with their attendance for the selected date
    query = '''
        SELECT s.id, s.student_name, s.usn,
               s.department, a.status
        FROM students s
        LEFT JOIN attendance a
        ON s.id = a.student_id AND a.date = ?
    '''

    students_data = conn.execute(
        query,
        (date,)
    ).fetchall()

    conn.close()

    return render_template(
        'attendance.html',
        students=students_data,
        date=date
    )


@app.route('/reports')
@login_required
def reports():

    conn = get_db_connection()

    query = '''
        SELECT
            s.id,
            s.student_name,
            s.usn,
            s.department,
            COUNT(a.id) as total_days,
            SUM(
                CASE
                    WHEN a.status = 'Present'
                    THEN 1
                    ELSE 0
                END
            ) as present_days
        FROM students s
        LEFT JOIN attendance a
        ON s.id = a.student_id
        GROUP BY s.id
    '''

    report_data = conn.execute(query).fetchall()

    conn.close()

    processed_report = []

    for row in report_data:

        r = dict(row)

        total = r['total_days']
        present = r['present_days'] or 0

        if total > 0:
            r['percentage'] = round((present / total) * 100, 2)

        else:
            r['percentage'] = 0.0

        processed_report.append(r)

    return render_template(
        'reports.html',
        report=processed_report
    )


@app.route('/api/chart-data')
@login_required
def chart_data():

    conn = get_db_connection()

    dates_query = conn.execute(
        'SELECT DISTINCT date FROM attendance ORDER BY date DESC LIMIT 7'
    ).fetchall()

    dates = [row['date'] for row in dates_query][::-1]

    present_data = []
    absent_data = []

    for d in dates:

        p_count = conn.execute(
            'SELECT COUNT(*) FROM attendance WHERE date = ? AND status = "Present"',
            (d,)
        ).fetchone()[0]

        a_count = conn.execute(
            'SELECT COUNT(*) FROM attendance WHERE date = ? AND status = "Absent"',
            (d,)
        ).fetchone()[0]

        present_data.append(p_count)
        absent_data.append(a_count)

    conn.close()

    return jsonify({
        'labels': dates,
        'present': present_data,
        'absent': absent_data
    })


@app.route('/export')
@login_required
def export_csv():

    conn = get_db_connection()

    query = '''
        SELECT
            s.usn,
            s.student_name,
            s.department,
            a.date,
            a.status
        FROM students s
        LEFT JOIN attendance a
        ON s.id = a.student_id
        ORDER BY a.date DESC, s.usn ASC
    '''

    data = conn.execute(query).fetchall()

    conn.close()

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    filename = f'attendance_report_{timestamp}.csv'

    filepath = os.path.join(EXPORT_DIR, filename)

    with open(filepath, 'w', newline='') as f:

        writer = csv.writer(f)

        writer.writerow([
            'USN',
            'Student Name',
            'Department',
            'Date',
            'Status'
        ])

        for row in data:

            writer.writerow([
                row['usn'],
                row['student_name'],
                row['department'],
                row['date'] if row['date'] else 'N/A',
                row['status'] if row['status'] else 'N/A'
            ])

    return send_file(filepath, as_attachment=True)


# IMPORTANT FOR DOCKER + VERCEL
if __name__ == '__main__':

    port = int(os.environ.get('PORT', 5000))

    app.run(
        host='0.0.0.0',
        port=port
    )
