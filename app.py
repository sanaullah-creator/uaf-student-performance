from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from functools import wraps
import re
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
import io
from openpyxl import Workbook
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)


# ====================== DATABASE CONNECTION ======================
def get_db_connection():
    try:
        return mysql.connector.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            database=app.config['MYSQL_DB']
        )
    except:
        return None


# ====================== LOGIN REQUIRED ======================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ====================== HOME ======================
@app.route('/')
def home():
    return redirect(url_for('login'))


# ====================== REGISTER ======================
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        name = request.form['name'].strip()
        email = request.form['email'].strip()
        password = request.form['password'].strip()

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT id FROM users WHERE email=%s", (email,))

        if cur.fetchone():
            flash('Email already exists!', 'danger')
            conn.close()
            return redirect(url_for('register'))

        hashed = generate_password_hash(password)

        cur.execute("""
            INSERT INTO users (name, email, password)
            VALUES (%s, %s, %s)
        """, (name, email, hashed))

        conn.commit()
        conn.close()

        flash('Registration successful!', 'success')

        return redirect(url_for('login'))

    return render_template('register.html')


# ====================== LOGIN ======================
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email'].strip()
        password = request.form['password'].strip()

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()

        conn.close()

        if user and check_password_hash(user[3], password):

            session['user_id'] = user[0]
            session['user_name'] = user[1]

            return redirect(url_for('dashboard'))

        else:
            flash('Invalid credentials!', 'danger')

    return render_template('login.html')


# ====================== LOGOUT ======================
@app.route('/logout')
def logout():

    session.clear()

    flash('Logged out successfully.', 'info')

    return redirect(url_for('login'))


# ====================== DASHBOARD ======================
@app.route('/dashboard')
@login_required
def dashboard():

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    search = request.args.get('search', '').strip()

    query = """
        SELECT 
            s.id,
            s.student_name,
            s.ag_number,
            s.degree,
            s.section,
            s.shift,
            s.created_at,

            COUNT(sub.id) AS subject_count,

            ROUND(AVG(sub.percentage), 2) AS avg_percentage,

            ROUND(AVG(sub.grade_point), 2) AS gpa

        FROM students s

        LEFT JOIN subjects sub
        ON s.id = sub.student_id

        WHERE s.user_id = %s
    """

    params = [session['user_id']]

    if search:
        query += """
            AND (
                s.student_name LIKE %s
                OR s.ag_number LIKE %s
            )
        """

        params.extend([
            f"%{search}%",
            f"%{search}%"
        ])

    query += """
        GROUP BY s.id
        ORDER BY s.created_at DESC
    """

    cur.execute(query, params)

    students = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'dashboard.html',
        students=students,
        search=search
    )


# ====================== ALL STUDENTS ======================
@app.route('/all_students')
@login_required
def all_students():

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    search = request.args.get('search', '').strip()

    query = """
        SELECT 
            s.id,
            s.student_name,
            s.ag_number,
            s.degree,
            s.section,
            s.shift,
            s.created_at,

            COUNT(sub.id) AS subject_count,

            ROUND(AVG(sub.percentage), 2) AS avg_percentage,

            ROUND(AVG(sub.grade_point), 2) AS gpa

        FROM students s

        LEFT JOIN subjects sub
        ON s.id = sub.student_id

        WHERE s.user_id = %s
    """

    params = [session['user_id']]

    if search:

        query += """
            AND (
                s.student_name LIKE %s
                OR s.ag_number LIKE %s
            )
        """

        params.extend([
            f"%{search}%",
            f"%{search}%"
        ])

    query += """
        GROUP BY s.id
        ORDER BY s.student_name ASC
    """

    cur.execute(query, params)

    students = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'all_students.html',
        students=students,
        search=search
    )


# ====================== PREDICTION / ADD STUDENT ======================
@app.route('/prediction', methods=['GET', 'POST'])
@login_required
def prediction():

    if request.method == 'POST':

        student_name = request.form.get('student_name', '').strip()

        ag_number = request.form.get('ag_number', '').strip()

        degree = request.form.get('degree', '').strip()

        section = request.form.get('section', '').strip()

        shift = request.form.get('shift', '').strip()

        if not student_name or not ag_number:
            flash('Student name and AG number are required.', 'danger')
            return redirect(url_for('prediction'))

        if not re.match(r"^\d{4}-AG-\d{4}$", ag_number):
            flash('AG Number must be like: 2024-AG-1234', 'danger')
            return redirect(url_for('prediction'))

        conn = get_db_connection()
        cur = conn.cursor()

        subject_count = 0

        try:

            # ====================== INSERT STUDENT ======================
            cur.execute("""
                INSERT INTO students
                (
                    user_id,
                    student_name,
                    ag_number,
                    degree,
                    section,
                    shift
                )

                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                session['user_id'],
                student_name,
                ag_number,
                degree,
                section,
                shift
            ))

            student_id = cur.lastrowid

            # ====================== SUBJECT LOOP ======================
            i = 1

            while True:

                subject_name = request.form.get(f'subject_name_{i}')

                if subject_name is None:
                    break

                subject_name = subject_name.strip()

                if not subject_name:
                    i += 1
                    continue

                subject_id = request.form.get(f'subject_id_{i}', '').strip()

                credit_hours = int(
                    request.form.get(f'credit_hours_{i}', 3)
                )

                mid_marks = float(
                    request.form.get(f'mid_{i}', 0)
                )

                sessional_marks = float(
                    request.form.get(f'sessional_{i}', 0)
                )

                final_marks = float(
                    request.form.get(f'final_{i}', 0)
                )

                total_marks = float(
                    request.form.get(f'total_{i}', 100)
                )

                # ====================== CALCULATE ======================
                obtained_marks = (
                    mid_marks +
                    sessional_marks +
                    final_marks
                )

                percentage = round(
                    (obtained_marks / total_marks) * 100,
                    2
                ) if total_marks > 0 else 0

                # ====================== GRADING ======================
                if percentage >= 85:
                    grade, gp, status = "A", 4.00, "Excellent"

                elif percentage >= 80:
                    grade, gp, status = "A-", 3.67, "Excellent"

                elif percentage >= 75:
                    grade, gp, status = "B+", 3.33, "Good"

                elif percentage >= 70:
                    grade, gp, status = "B", 3.00, "Good"

                elif percentage >= 65:
                    grade, gp, status = "B-", 2.67, "Good"

                elif percentage >= 61:
                    grade, gp, status = "C+", 2.33, "Medium"

                elif percentage >= 58:
                    grade, gp, status = "C", 2.00, "Medium"

                elif percentage >= 55:
                    grade, gp, status = "C-", 1.67, "Medium"

                elif percentage >= 50:
                    grade, gp, status = "D", 1.00, "Weak"

                else:
                    grade, gp, status = "F", 0.5, "Fail"

                # ====================== INSERT SUBJECT ======================
                cur.execute("""
                    INSERT INTO subjects
                    (
                        student_id,
                        subject_name,
                        subject_id,
                        credit_hours,
                        mid_marks,
                        sessional_marks,
                        final_marks,
                        obtained_marks,
                        total_marks,
                        percentage,
                        grade,
                        grade_point,
                        status
                    )

                    VALUES
                    (
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s
                    )
                """, (
                    student_id,
                    subject_name,
                    subject_id,
                    credit_hours,
                    mid_marks,
                    sessional_marks,
                    final_marks,
                    obtained_marks,
                    total_marks,
                    percentage,
                    grade,
                    gp,
                    status
                ))

                subject_count += 1

                i += 1

            conn.commit()

            flash(
                f'✅ {student_name} added successfully with {subject_count} subject(s)!',
                'success'
            )

        except Exception as e:

            conn.rollback()

            flash(f'❌ Error: {str(e)}', 'danger')

        finally:

            cur.close()
            conn.close()

        return redirect(url_for('dashboard'))

    return render_template('prediction.html')


# ====================== STUDENT DETAIL ======================
@app.route('/student/<int:student_id>')
@login_required
def student_detail(student_id):

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT *
        FROM students
        WHERE id = %s
        AND user_id = %s
    """, (
        student_id,
        session['user_id']
    ))

    student = cur.fetchone()

    if not student:

        flash('Student not found!', 'danger')

        return redirect(url_for('dashboard'))

    cur.execute("""
        SELECT *
        FROM subjects
        WHERE student_id = %s
        ORDER BY subject_name
    """, (student_id,))

    subjects = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'student_detail.html',
        student=student,
        subjects=subjects
    )


# ====================== EDIT STUDENT ======================
@app.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    if request.method == 'POST':

        student_name = request.form['student_name'].strip()

        ag_number = request.form['ag_number'].strip()

        degree = request.form['degree'].strip()

        section = request.form['section'].strip()

        shift = request.form['shift'].strip()

        try:

            cur.execute("""
                UPDATE students

                SET
                    student_name=%s,
                    ag_number=%s,
                    degree=%s,
                    section=%s,
                    shift=%s

                WHERE id=%s
                AND user_id=%s
            """, (
                student_name,
                ag_number,
                degree,
                section,
                shift,
                student_id,
                session['user_id']
            ))

            conn.commit()

            flash('✅ Student updated successfully!', 'success')

            return redirect(url_for('dashboard'))

        except Exception as e:

            flash(f'❌ Error: {str(e)}', 'danger')

    cur.execute("""
        SELECT *
        FROM students
        WHERE id = %s
        AND user_id = %s
    """, (
        student_id,
        session['user_id']
    ))

    student = cur.fetchone()

    cur.close()
    conn.close()

    if not student:

        flash('Student not found!', 'danger')

        return redirect(url_for('dashboard'))

    return render_template(
        'edit_student.html',
        student=student
    )


# ====================== DELETE STUDENT ======================
@app.route('/delete_student/<int:student_id>', methods=['POST'])
@login_required
def delete_student(student_id):

    conn = get_db_connection()
    cur = conn.cursor()

    try:

        cur.execute("""
            DELETE FROM subjects
            WHERE student_id = %s
        """, (student_id,))

        cur.execute("""
            DELETE FROM students
            WHERE id = %s
            AND user_id = %s
        """, (
            student_id,
            session['user_id']
        ))

        conn.commit()

        flash('Student record deleted successfully.', 'success')

    except:

        flash('Error deleting record.', 'danger')

    finally:

        cur.close()
        conn.close()

    return redirect(url_for('dashboard'))


# ====================== EXPORT EXCEL ======================
@app.route('/export_excel')
@login_required
def export_excel():

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT

            s.student_name,
            s.ag_number,
            s.degree,
            s.section,
            s.shift,

            sub.subject_name,
            sub.subject_id,
            sub.credit_hours,
            sub.mid_marks,
            sub.sessional_marks,
            sub.final_marks,
            sub.obtained_marks,
            sub.total_marks,
            sub.percentage,
            sub.grade,
            sub.grade_point,
            sub.status

        FROM students s

        JOIN subjects sub
        ON s.id = sub.student_id

        WHERE s.user_id = %s

        ORDER BY s.student_name, sub.subject_name
    """, (session['user_id'],))

    records = cur.fetchall()

    cur.close()
    conn.close()

    wb = Workbook()

    ws = wb.active

    ws.title = "Student Performance"

    headers = [
        "Student Name",
        "AG Number",
        "Degree",
        "Section",
        "Shift",
        "Subject Name",
        "Subject ID",
        "Credit Hours",
        "Mid Marks",
        "Sessional Marks",
        "Final Marks",
        "Obtained Marks",
        "Total Marks",
        "Percentage",
        "Grade",
        "Grade Point",
        "Status"
    ]

    ws.append(headers)

    for row in records:

        ws.append([
            row['student_name'],
            row['ag_number'],
            row['degree'],
            row['section'],
            row['shift'],
            row['subject_name'],
            row['subject_id'],
            row['credit_hours'],
            row['mid_marks'],
            row['sessional_marks'],
            row['final_marks'],
            row['obtained_marks'],
            row['total_marks'],
            row['percentage'],
            row['grade'],
            row['grade_point'],
            row['status']
        ])

    output = io.BytesIO()

    wb.save(output)

    output.seek(0)

    filename = f"Performance_Report_{datetime.now().strftime('%Y-%m-%d')}.xlsx"

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)