import sqlite3
import hashlib
import csv
from datetime import date
from getpass import getpass

DB_NAME = "student_management.db"

def password_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_tables()

    def create_tables(self):
        statements = [
            "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY, roll_no TEXT UNIQUE NOT NULL, first_name TEXT NOT NULL, last_name TEXT NOT NULL, department TEXT NOT NULL, year INTEGER NOT NULL, section TEXT, phone TEXT, email TEXT, active INTEGER DEFAULT 1)",
            "CREATE TABLE IF NOT EXISTS courses (id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL, name TEXT NOT NULL, department TEXT NOT NULL, credits INTEGER NOT NULL)",
            "CREATE TABLE IF NOT EXISTS enrollments (id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL, course_id INTEGER NOT NULL, academic_year TEXT NOT NULL, UNIQUE(student_id,course_id,academic_year), FOREIGN KEY(student_id) REFERENCES students(id), FOREIGN KEY(course_id) REFERENCES courses(id))",
            "CREATE TABLE IF NOT EXISTS attendance (id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL, course_id INTEGER NOT NULL, day TEXT NOT NULL, status TEXT NOT NULL, UNIQUE(student_id,course_id,day), FOREIGN KEY(student_id) REFERENCES students(id), FOREIGN KEY(course_id) REFERENCES courses(id))",
            "CREATE TABLE IF NOT EXISTS grades (id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL, course_id INTEGER NOT NULL, exam TEXT NOT NULL, marks REAL NOT NULL, maximum REAL NOT NULL, UNIQUE(student_id,course_id,exam), FOREIGN KEY(student_id) REFERENCES students(id), FOREIGN KEY(course_id) REFERENCES courses(id))",
            "CREATE TABLE IF NOT EXISTS fees (id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL, fee_type TEXT NOT NULL, amount REAL NOT NULL, paid REAL DEFAULT 0, due_date TEXT NOT NULL, FOREIGN KEY(student_id) REFERENCES students(id))"
        ]
        for statement in statements:
            self.conn.execute(statement)
        if not self.one("SELECT id FROM users WHERE username=?", ("admin",)):
            self.execute("INSERT INTO users(username,password,role) VALUES(?,?,?)", ("admin", password_hash("admin123"), "admin"))
        self.conn.commit()

    def execute(self, sql, params=()):
        result = self.conn.execute(sql, params)
        self.conn.commit()
        return result

    def all(self, sql, params=()):
        return self.conn.execute(sql, params).fetchall()

    def one(self, sql, params=()):
        return self.conn.execute(sql, params).fetchone()

def ask(label, required=True, default=None):
    suffix = "" if default is None else f" [{default}]"
    value = input(f"{label}{suffix}: ").strip()
    if not value and default is not None:
        return str(default)
    if required and not value:
        print("This field is required.")
        return ask(label, required, default)
    return value

def header(text):
    print("\n" + "=" * 70)
    print(text.center(70))
    print("=" * 70)

def pause():
    input("\nPress Enter to continue...")

def student_id(db):
    key = ask("Student ID or roll number")
    row = db.one("SELECT id FROM students WHERE id=? OR roll_no=?", (key, key))
    if not row:
        print("Student not found.")
        return None
    return row["id"]

def add_student(db):
    header("ADD STUDENT")
    data = (ask("Roll number"), ask("First name"), ask("Last name"), ask("Department"), int(ask("Year")), ask("Section", False), ask("Phone", False), ask("Email", False))
    try:
        db.execute("INSERT INTO students(roll_no,first_name,last_name,department,year,section,phone,email) VALUES(?,?,?,?,?,?,?,?)", data)
        print("Student added successfully.")
    except sqlite3.IntegrityError:
        print("That roll number already exists.")

def list_students(db):
    header("ACTIVE STUDENTS")
    rows = db.all("SELECT id,roll_no,first_name,last_name,department,year,section FROM students WHERE active=1 ORDER BY roll_no")
    print(f"{'ID':<5}{'ROLL':<14}{'NAME':<25}{'DEPARTMENT':<15}{'YEAR':<6}SECTION")
    for r in rows:
        print(f"{r['id']:<5}{r['roll_no']:<14}{(r['first_name']+' '+r['last_name']):<25}{r['department']:<15}{r['year']:<6}{r['section'] or '-'}")
    print(f"\nTotal: {len(rows)}")

def search_students(db):
    term = ask("Search term")
    rows = db.all("SELECT * FROM students WHERE roll_no LIKE ? OR first_name LIKE ? OR last_name LIKE ? OR department LIKE ?", tuple([f"%{term}%"] * 4))
    for r in rows:
        print(f"{r['id']} | {r['roll_no']} | {r['first_name']} {r['last_name']} | {r['department']} | Year {r['year']}")
    print(f"{len(rows)} result(s).")

def update_student(db):
    sid = student_id(db)
    if not sid: return
    s = db.one("SELECT * FROM students WHERE id=?", (sid,))
    phone = ask("Phone", False, s["phone"] or "")
    email = ask("Email", False, s["email"] or "")
    section = ask("Section", False, s["section"] or "")
    db.execute("UPDATE students SET phone=?,email=?,section=? WHERE id=?", (phone,email,section,sid))
    print("Student updated.")

def manage_students(db):
    while True:
        header("STUDENTS")
        print("1. Add  2. List  3. Search  4. Update  5. Deactivate  0. Back")
        choice = ask("Option")
        if choice == "0": return
        if choice == "1": add_student(db)
        elif choice == "2": list_students(db)
        elif choice == "3": search_students(db)
        elif choice == "4": update_student(db)
        elif choice == "5":
            sid = student_id(db)
            if sid: db.execute("UPDATE students SET active=0 WHERE id=?", (sid,)); print("Student deactivated.")
        else: print("Invalid option.")
        pause()

def manage_courses(db):
    while True:
        header("COURSES")
        print("1. Add course  2. List courses  3. Delete course  0. Back")
        choice = ask("Option")
        if choice == "0": return
        if choice == "1":
            try:
                db.execute("INSERT INTO courses(code,name,department,credits) VALUES(?,?,?,?)", (ask("Code"),ask("Name"),ask("Department"),int(ask("Credits"))))
                print("Course added.")
            except sqlite3.IntegrityError: print("Course code already exists.")
        elif choice == "2":
            for r in db.all("SELECT * FROM courses ORDER BY code"):
                print(f"{r['id']} | {r['code']} | {r['name']} | {r['department']} | {r['credits']} credits")
        elif choice == "3":
            db.execute("DELETE FROM courses WHERE id=?", (ask("Course ID"),)); print("Deletion completed.")
        pause()

def enroll(db):
    sid = student_id(db)
    if not sid: return
    try:
        db.execute("INSERT INTO enrollments(student_id,course_id,academic_year) VALUES(?,?,?)", (sid,ask("Course ID"),ask("Academic year",True,"2026-2027")))
        print("Enrollment saved.")
    except sqlite3.IntegrityError: print("Invalid or duplicate enrollment.")

def record_attendance(db):
    sid = student_id(db)
    if not sid: return
    status = ask("Status Present/Absent/Late", True, "Present").title()
    if status not in ("Present","Absent","Late"): print("Invalid status."); return
    try:
        db.execute("INSERT INTO attendance(student_id,course_id,day,status) VALUES(?,?,?,?)", (sid,ask("Course ID"),ask("Date YYYY-MM-DD",True,date.today().isoformat()),status))
        print("Attendance recorded.")
    except sqlite3.IntegrityError: print("Attendance already exists for this student/course/date.")

def record_grade(db):
    sid = student_id(db)
    if not sid: return
    try:
        db.execute("INSERT INTO grades(student_id,course_id,exam,marks,maximum) VALUES(?,?,?,?,?)", (sid,ask("Course ID"),ask("Exam name"),float(ask("Marks")),float(ask("Maximum marks"))))
        print("Grade recorded.")
    except sqlite3.IntegrityError: print("Duplicate grade or invalid course.")

def manage_fees(db):
    header("FEES")
    print("1. Add fee  2. Make payment  3. Outstanding fees")
    choice=ask("Option")
    if choice=="1":
        sid=student_id(db)
        if sid: db.execute("INSERT INTO fees(student_id,fee_type,amount,due_date) VALUES(?,?,?,?)",(sid,ask("Fee type"),float(ask("Amount")),ask("Due date YYYY-MM-DD"))); print("Fee created.")
    elif choice=="2":
        db.execute("UPDATE fees SET paid=paid+? WHERE id=?",(float(ask("Payment amount")),ask("Fee ID"))); print("Payment recorded.")
    elif choice=="3":
        rows=db.all("SELECT f.id,s.roll_no,s.first_name||' '||s.last_name name,f.fee_type,f.amount-f.paid balance,f.due_date FROM fees f JOIN students s ON s.id=f.student_id WHERE f.amount>f.paid")
        for r in rows: print(f"{r['id']} | {r['roll_no']} | {r['name']} | {r['fee_type']} | Due: {r['balance']:.2f} | {r['due_date']}")

def reports(db):
    header("REPORTS")
    print("1. Dashboard  2. Attendance percentage  3. Grade report")
    choice=ask("Option")
    if choice=="1":
        print("Active students:",db.one("SELECT COUNT(*) n FROM students WHERE active=1")["n"])
        print("Courses:",db.one("SELECT COUNT(*) n FROM courses")["n"])
        print("Outstanding fees:",db.one("SELECT COALESCE(SUM(amount-paid),0) n FROM fees")["n"])
    elif choice in ("2","3"):
        sid=student_id(db)
        if not sid:return
        if choice=="2":
            rows=db.all("SELECT c.code,COUNT(*) total,SUM(CASE WHEN a.status!='Absent' THEN 1 ELSE 0 END) present FROM attendance a JOIN courses c ON c.id=a.course_id WHERE a.student_id=? GROUP BY c.id",(sid,))
            for r in rows: print(f"{r['code']}: {r['present']}/{r['total']} = {100*r['present']/r['total']:.1f}%")
        else:
            rows=db.all("SELECT c.code,g.exam,g.marks,g.maximum FROM grades g JOIN courses c ON c.id=g.course_id WHERE g.student_id=?",(sid,))
            for r in rows: print(f"{r['code']} | {r['exam']} | {r['marks']}/{r['maximum']} ({100*r['marks']/r['maximum']:.1f}%)")

def export_students(db):
    filename=ask("CSV file name",True,"students.csv")
    rows=db.all("SELECT roll_no,first_name,last_name,department,year,section,phone,email,active FROM students")
    with open(filename,"w",newline="",encoding="utf-8") as f:
        writer=csv.writer(f); writer.writerow(["roll_no","first_name","last_name","department","year","section","phone","email","active"])
        writer.writerows([tuple(r) for r in rows])
    print(f"Exported {len(rows)} students to {filename}.")

def login(db):
    header("STUDENT MANAGEMENT SYSTEM")
    for _ in range(3):
        username=ask("Username")
        password=getpass("Password: ")
        user=db.one("SELECT * FROM users WHERE username=? AND password=?",(username,password_hash(password)))
        if user: print(f"Logged in as {user['username']}."); return True
        print("Invalid login.")
    return False

def main():
    db=Database()
    if not login(db): return
    while True:
        header("MAIN MENU")
        print("1. Students  2. Courses  3. Enroll student  4. Attendance")
        print("5. Grades    6. Fees     7. Reports         8. Export CSV")
        print("0. Exit")
        choice=ask("Option")
        if choice=="0": print("Goodbye."); break
        actions={"1":manage_students,"2":manage_courses,"3":enroll,"4":record_attendance,"5":record_grade,"6":manage_fees,"7":reports,"8":export_students}
        if choice in actions: actions[choice](db); pause()
        else: print("Invalid option.")

if __name__ == "__main__":
    main()
