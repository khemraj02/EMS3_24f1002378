from flask import current_app as app, flash, request, url_for
from .models import *
from flask import render_template, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_
from flask_security import login_user, roles_required, current_user
from flask import jsonify
import csv

# ------------------------------------------ Adminer functionality ---------------------------- 
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register/<role>", methods=["GET","POST"])
def register(role):
    if request.method == "POST":
        username = request.form.get("username")
        email  = request.form.get("email")
        mob = request.form.get("mob")
        department  = request.form.get("department")
        password  = request.form.get("password")
        
        old_user = User.query.filter_by(email=email).first()
        if old_user:
            return "User alreday exist !!"
        else:
            if role == "Student":
                new_user = app.security.datastore.create_user(username=username, email=email, 
                                                              password=generate_password_hash(password))
                roles = app.security.datastore.find_role("student")
                new_user.roles.append(roles)
                new = Student(user_id=new_user.id, mob=mob, department=department)
            else:
                new_user = app.security.datastore.create_user(username=username,
                            email=email, active=False,password=generate_password_hash(password))
                roles = app.security.datastore.find_role("examiner")
                new_user.roles.append(roles)
                new = Examiner(user_id=new_user.id, mob=mob, department=department)
            db.session.add(new_user)
            db.session.add(new)
            db.session.commit()
            return "Registration Successful !!"
    return render_template("register.html", role=role)

@app.route("/login/0", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = app.security.datastore.find_user(email=email)
        if user:
            if check_password_hash(user.password, password):
                if user.has_role("admin"):
                    login_user(user)
                    return redirect("/admin/dashboard")
                elif user.has_role("student"):
                    if user.active:
                        login_user(user)
                        return redirect("/student/dashboard")
                    else:
                        return "Your account has been blacklisted !!"
                else:
                    if user.examiner.status == "Pending":
                        return "Waiting for admin's approval"
                    elif user.examiner.status == "Blacklisted":
                        return "Your account has been blacklisted !!"
                    else:
                        login_user(user)
                        return redirect(url_for("examiner_dashboard"))
            else:
                return "Incorrect password !!"
        else:
            return "User doesn't exist !!"
    return render_template("login.html")

@app.route("/admin/dashboard")
@roles_required("admin")
def admin_dashboard():
    courses = Course.query.count()
    active_courses = Course.query.filter_by(status="Active").count()

    students = Student.query.count()
    exams = Exam.query.count()
    upcoming_exams = Exam.query.filter(
        Exam.scsd >= date.today(),
        Exam.status != "Completed"
    ).count()

    bookings = Booking.query.count()
    completed_bookings = Booking.query.filter_by(
        status="Completed"
    ).count()

    examiners = Examiner.query.count()
    slots = Slot.query.count()

    available_slots = Slot.query.filter(
        Slot.avl_seat > 0,
        Slot.status == "Booking Open"
    ).count()

    pending_evaluations = Booking.query.filter_by(
        status="Completed"
    ).count()

    total_evaluations = Evaluation.query.count()

    return render_template(
        "admin_dashboard.html",
        courses=courses,
        active_courses=active_courses,
        students=students,
        exams=exams,
        upcoming_exams=upcoming_exams,
        bookings=bookings,
        completed_bookings=completed_bookings,
        examiners=examiners,
        slots=slots,
        available_slots=available_slots,
        pending_evaluations=pending_evaluations,
        total_evaluations=total_evaluations
    )
    
@app.route("/admin/dashboard/statistics", methods=["GET"])
@roles_required("admin")
def admin_dashboard_statistics():

    # Collect examination-related statistics
    total_courses = Course.query.count()
    active_courses = Course.query.filter_by(status="Active").count()

    total_exams = Exam.query.count()
    upcoming_exams = Exam.query.filter(
        Exam.scsd >= date.today()
    ).count()

    total_students = Student.query.count()
    total_examiners = Examiner.query.count()

    total_slots = Slot.query.count()
    available_slots = Slot.query.filter(
        Slot.avl_seat > 0,
        Slot.status == "Booking Open"
    ).count()

    total_bookings = Booking.query.count()
    completed_bookings = Booking.query.filter_by(
        status="Completed"
    ).count()

    # Prepare statistics for the dashboard
    statistics_data = {
        "courses": {
            "total": total_courses,
            "active": active_courses
        },
        "examinations": {
            "total": total_exams,
            "upcoming": upcoming_exams
        },
        "users": {
            "students": total_students,
            "examiners": total_examiners
        },
        "slots": {
            "total": total_slots,
            "available": available_slots
        },
        "bookings": {
            "total": total_bookings,
            "completed": completed_bookings
        }
    }

    return jsonify(statistics_data)
@app.route("/admin/manage/courses", methods=["GET","POST"])
def manage_courses():
    edit_id = request.args.get("edit_id", type=int)
    edit_course = db.session.get(Course, edit_id) if edit_id else None
    
    if request.method == "POST":
        code = request.form.get("code","")
        name = request.form.get("name","")
        status = request.form.get("status","Pending")
        description = request.form.get("description","")
        
        if Course.query.filter(Course.code==code, Course.id != (edit_id or 0)).first():
            return "Course already exist !!"
        else:
            course = edit_course or Course()
            course.code = code
            course.name = name
            course.description = description
            course.status = status
            if not edit_course:
                db.session.add(course)
            db.session.commit()
            return ("Course Updated successfully" if edit_course else "Course added successfully !!")
        
    search = request.args.get("search","")
    courses = Course.query.all() 
        
    if search:
        result = Course.query.filter(or_(
            Course.code.ilike(f"%{search}%"), 
            Course.name.ilike(f"%{search}%")
        )).all()
        if search.isdigit():
            result = Course.query.filter_by(id=int(search)).all()
        courses = result
        print(courses)
    return render_template("manage_courses.html", courses=courses, edit_course=edit_course, search=search)


@app.route("/admin/delete/course")
def delete_course():
    course_id = request.args.get("course_id")
    course = Course.query.get(course_id)
    course.status = "Deleted"
    db.session.commit()
    return redirect(url_for("manage_courses"))

@app.route("/admin/manage/examiners")
def manage_examiners():
    examiners = Examiner.query.all()
    search = request.args.get("search","")
    examiners = Examiner.query.all()
    
    if search:
        result = Examiner.query.join(Examiner.user).filter(or_(
            User.username.ilike(f"%{search}%"),
            User.email.ilike(f"%{search}%"),
            Examiner.department.ilike(f"%{search}%"),
            Examiner.status.ilike(f"%{search}%")
        )).all()
        if search.isdigit():
            result = Examiner.query.filter_by(id=search).all()
        examiners = result
    return render_template("manage_examiners.html", examiners=examiners, search=search)


@app.route("/admin/update/examiner/<action>/<int:examiner_id>")
def update_examiner_status(action,examiner_id):
    examiner = Examiner.query.get(examiner_id)
    if action == "approve":
        examiner.status = "Active"
        examiner.user.active = True
    else:
        examiner.status = "Blacklisted"
        examiner.user.active = False
    db.session.commit()
    return redirect(url_for("manage_examiners"))

from datetime import date
@app.route("/admin/manage/exams", methods=["GET","POST"] )
def manage_exams():
    edit_id = request.args.get("edit_id")
    edit_exam = db.session.get(Exam, int(edit_id)) if edit_id else None
    if request.method == "POST":
        course_id = request.form.get("course_id")
        examiner_id = request.form.get("examiner_id")
        name = request.form.get("name")
        type = request.form.get("type")
        duration = request.form.get("duration")
        max_marks = request.form.get("max_marks")
        scsd= request.form.get("scsd")
        sced = request.form.get("sced")
        sbsd = request.form.get("sbsd")
        sbed = request.form.get("sbed")
        status = request.form.get("status")
        
        exam = edit_exam or Exam()
        exam.course_id = course_id
        exam.examiner_id = examiner_id
        exam.name = name
        exam.type = type
        exam.duration = duration
        exam.max_marks = max_marks
        exam.scsd = date.fromisoformat(scsd)
        exam.sced = date.fromisoformat(sced)
        exam.sbsd = date.fromisoformat(sbsd)
        exam.sbed = date.fromisoformat(sbed)
        exam.status = status
        
        if exam.sced < exam.scsd or exam.sbed < exam.sbsd:
            return "End date cannot be before start date"
        
        if not edit_exam:
            db.session.add(exam)
        db.session.commit()
        return "Examination created successfully !!"

    exams = Exam.query.all()
    search = request.args.get("search","")
    
    if search:
        result = Exam.query.join(Exam.course).filter(or_(
            Exam.name.ilike(f"%{search}%"),
            Course.code.ilike(f"%{search}%"),
            Exam.type.ilike(f"%{search}%")
        )).all()
        if search.isdigit():
            result = Exam.query.filter_by(id=search).all()
        exams = result
        
    courses = Course.query.filter_by(status="Active").all()
    examiners = Examiner.query.join(Examiner.user).filter(User.active.is_(True), Examiner.status=="Active").all()
    return render_template("manage_exams.html", courses=courses, exams=exams, edit_exam=edit_exam, search=search, examiners=examiners)

@app.route("/admin/exams/delete/<int:exam_id>", methods=["POST"])
def delete_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    db.session.delete(exam)
    db.session.commit()
    flash("Examination deleted successfully", "success")
    return redirect(url_for("manage_exams"))

@app.route("/admin/manage/students", methods=["GET", "POST"])
def manage_students():
    if request.method == "POST":
        student_id = request.args.get("student_id")
        student = Student.query.get(student_id)
        student.user.active = False
        db.session.commit()
        return "Student Blacklisted"
    students = Student.query.all()
    search = request.args.get("search", "").strip()

    if search:
        result = Student.query.join(Student.user).filter(or_(
            User.username.ilike(f"%{search}%"),
            User.email.ilike(f"%{search}%"),
            Student.department.ilike(f"%{search}%")
        )).all()

        if search.isdigit():
            result = Student.query.filter_by(id=search).all()
        students = result
    return render_template("manage_students.html", students=students, search=search)

from datetime import datetime
@app.route("/admin/manage/slots", methods=["GET","POST"])
def manage_slots():
    edit_id = request.args.get("edit_id")
    edit_slot = db.session.get(Slot, int(edit_id)) if edit_id else None

    if request.method == "POST":
        exam_id = request.form.get("exam_id", type=int)
        examiner_id = request.form.get("examiner_id", type=int)
        st = datetime.fromisoformat(request.form.get("st"))
        et = datetime.fromisoformat(request.form.get("et"))
        capacity = request.form.get("capacity", type=int)
        status = request.form.get("status")

        q = Slot.query.filter(Slot.examiner_id == examiner_id, Slot.st < et, Slot.et > st)
        if edit_slot:
            q = q.filter(Slot.id != edit_slot.id)
        overlap = q.first()
        
        if overlap:
            return "This examiner already has slot at this time !!"
        else:
            slot = edit_slot or Slot()
            slot.exam_id = exam_id
            slot.examiner_id = examiner_id
            slot.st = st
            slot.et = et
            if edit_slot and edit_slot.capacity != capacity:
                slot.avl_seat += capacity - edit_slot.capacity
            slot.capacity = capacity
            if not edit_slot:
                slot.avl_seat = capacity
            slot.status = status

            if not edit_slot:
                db.session.add(slot)
            db.session.commit()
            return ("Slot updated" if edit_slot else "Slot created")

    slots = Slot.query.order_by(Slot.st.desc(), Slot.et).all()
    search = request.args.get("search","")
    if search:
        result = Slot.query.join(Slot.exam).join(Exam.course).join(Slot.examiner).join(Examiner.user).filter(or_(
            Exam.name.ilike(f"%{search}%"),
            Course.name.ilike(f"%{search}%"),
            Slot.status.ilike(f"%{search}%"),
            User.username.ilike(f"%{search}%")
        )).all()

        if search.isdigit():
            result = Slot.query.filter_by(id=search).all()
        slots = result
    exams = Exam.query.filter(Exam.status != "Completed").all()
    examiners = Examiner.query.join(Examiner.user).filter(User.active.is_(True), Examiner.status=="Active").all()
    return render_template("manage_slots.html", exams=exams, examiners=examiners, slots=slots, edit_slot=edit_slot, search=search)

@app.route("/admin/delete/slot")
def delete_slot():
    slot_id = request.args.get("slot_id")
    slot = Slot.query.get(slot_id)
    if Booking.query.filter_by(slot_id=slot_id).first():
        return "Cannot be deleted because has bookings"
    else:
        db.session.delete(slot)
        db.session.commit() 
        return "Slot deleted !!"

@app.route("/admin/manage/rubrics", methods=["GET","POST"])
def manage_rubrics():
    edit_id = request.args.get("edit_id", type=int)
    edit_rubric = Rubric.query.get(edit_id) if edit_id else None

    if request.method == "POST":
        exam_id = request.form.get("exam_id", type=int)
        criteria = request.form.get("criteria")
        max_marks = request.form.get("max_marks", type=int)
        weightage = request.form.get("weightage", type=int)
        description = request.form.get("description")

        rubric = edit_rubric or Rubric()
        rubric.exam_id = exam_id
        rubric.criteria = criteria
        rubric.max_marks = max_marks
        rubric.weightage = weightage
        rubric.description = description

        if not edit_rubric:
            db.session.add(rubric)
        db.session.commit()
        return ("Rubric updated" if edit_rubric else "Rubic created successfully !!")

    rubrics = Rubric.query.all()
    search = request.args.get("search","").strip()
    if search:
        result = Rubric.query.join(Rubric.exam).join(Exam.course).filter(or_(
            Rubric.criteria.ilike(f"%{search}%"),
            Exam.name.ilike(f"%{search}%"),
            Course.code.ilike(f"%{search}%"),
            Course.name.ilike(f"%{search}%")
        )).all()
        if search.isdigit():
            result = Rubric.query.filter_by(id=search).all()
        rubrics = result
    exams = Exam.query.all()
    return render_template("manage_rubrics.html", exams=exams, rubrics=rubrics, search=search, edit_rubric=edit_rubric)

@app.route("/admin/delete/rubric")
def delete_rubric():
    id = request.args.get("rubric_id")
    rubric = Rubric.query.get(id)
    db.session.delete(rubric)
    db.session.commit()
    return "Rubric deleted !!"


# ============================================================
# ADDITIONAL REPORTING AND DATA EXPORT FUNCTIONALITY
# ============================================================

def generate_booking_csv(booking_records, report_title):
    """
    Generate a CSV report using the supplied booking records.

    This helper function is shared by the admin and examiner
    reporting routes.
    """

    output = BytesIO()

    # Use a text buffer to prepare CSV data.
    import io
    text_buffer = io.StringIO()

    writer = csv.writer(text_buffer)

    # Report heading
    writer.writerow([report_title])
    writer.writerow([])

    # Column headings
    writer.writerow([
        "Booking ID",
        "Student Name",
        "Student Email",
        "Department",
        "Course Code",
        "Course Name",
        "Examination",
        "Exam Type",
        "Slot ID",
        "Exam Date",
        "Booking Date",
        "Booking Status"
    ])

    # Add booking information
    for booking in booking_records:

        student = booking.student
        user = student.user
        slot = booking.slot
        exam = slot.exam
        course = exam.course

        exam_date = (
            slot.st.strftime("%d-%m-%Y")
            if slot.st else "Not Available"
        )

        booking_date = (
            booking.date.strftime("%d-%m-%Y")
            if booking.date else "Not Available"
        )

        writer.writerow([
            booking.id,
            user.username,
            user.email,
            student.department,
            course.code,
            course.name,
            exam.name,
            exam.type,
            slot.id,
            exam_date,
            booking_date,
            booking.status
        ])

    # Convert CSV text into downloadable bytes.
    output.write(text_buffer.getvalue().encode("utf-8-sig"))
    output.seek(0)

    return send_file(
        output,
        mimetype="text/csv",
        as_attachment=True,
        download_name="booking_report.csv"
    )


# ============================================================
# ADMIN BOOKING REPORT
# ============================================================

@app.route("/admin/reports/bookings", methods=["GET"])
@roles_required("admin")
def admin_booking_report():

    # Read optional filters from the URL.
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

    # Retrieve booking records.
    bookings = Booking.query.order_by(
        Booking.date.desc()
    ).all()

    # Filter by student name or email.
    if search:
        bookings = [
            booking for booking in bookings
            if search.lower() in booking.student.user.username.lower()
            or search.lower() in booking.student.user.email.lower()
        ]

    # Filter by booking status.
    if status:
        bookings = [
            booking for booking in bookings
            if booking.status.lower() == status.lower()
        ]

    # Filter by starting date.
    if start_date:
        try:
            selected_start = date.fromisoformat(start_date)

            bookings = [
                booking for booking in bookings
                if booking.date and (
                    booking.date.date()
                    if hasattr(booking.date, "date")
                    else booking.date
                ) >= selected_start
            ]

        except ValueError:
            return "Invalid starting date. Use YYYY-MM-DD."

    # Filter by ending date.
    if end_date:
        try:
            selected_end = date.fromisoformat(end_date)

            bookings = [
                booking for booking in bookings
                if booking.date and (
                    booking.date.date()
                    if hasattr(booking.date, "date")
                    else booking.date
                ) <= selected_end
            ]

        except ValueError:
            return "Invalid ending date. Use YYYY-MM-DD."

    # Generate the final report.
    return generate_booking_csv(
        bookings,
        "ADMIN BOOKING REPORT"
    )


# ============================================================
# EXAMINER BOOKING REPORT
# ============================================================

@app.route("/examiner/reports/bookings", methods=["GET"])
@roles_required("examiner")
def examiner_booking_report():

    examiner = current_user.examiner

    # Retrieve only bookings belonging to this examiner's slots.
    bookings = Booking.query.join(
        Booking.slot
    ).filter(
        Slot.examiner_id == examiner.id
    ).order_by(
        Booking.date.desc()
    ).all()

    # Optional status filter.
    selected_status = request.args.get(
        "status", ""
    ).strip()

    if selected_status:
        bookings = [
            booking for booking in bookings
            if booking.status.lower() == selected_status.lower()
        ]

    # Optional student search.
    student_search = request.args.get(
        "search", ""
    ).strip()

    if student_search:
        bookings = [
            booking for booking in bookings
            if student_search.lower()
            in booking.student.user.username.lower()
        ]

    return generate_booking_csv(
        bookings,
        "EXAMINER BOOKING REPORT"
    )


# ------------------------------------Examiner Functionality -------------------------------------------------
@app.route("/examiner/dashboard")
@roles_required("examiner")
def examiner_dashboard():
    examiner = current_user.examiner
    total_exams = len(examiner.exams)
    upcoming_slots = Slot.query.filter(Slot.examiner_id==examiner.id, Slot.st >= date.today(), Slot.status != "Completed").all()
    total_bookings = Booking.query.join(Booking.slot).filter(Slot.examiner_id == examiner.id).count()
    examiner_slots = examiner.slots
    pending_eval = 0
    for slot in examiner_slots:
        for book in slot.bookings:
            if book.status == "Completed":
                pending_eval += 1
    return render_template("examiner_dashboard.html", total_exams=total_exams, upcoming_slots=upcoming_slots,
                           pending_eval=pending_eval, total_bookings=total_bookings)


@app.route("/examiner/exams", methods=["GET","POST"])
@roles_required("examiner")
def examiner_exams():
    exam_id = request.args.get("exam_id")
    exam = Exam.query.get(exam_id) if exam_id else None
    if request.method == "POST":
        examiner_id = current_user.examiner.id
        st = datetime.fromisoformat(request.form.get("st"))
        et = datetime.fromisoformat(request.form.get("et"))
        capacity = request.form.get("capacity", type=int)
        status = request.form.get("status")

        overlap = Slot.query.filter(Slot.examiner_id==examiner_id, Slot.st < st, Slot.et > st).first()

        if overlap:
            return "You already has slot at this time !!"
        else:
            slot = Slot()
            slot.exam_id = exam_id
            slot.examiner_id = examiner_id
            slot.st = st
            slot.et = et
            slot.capacity = capacity
            slot.avl_seat = capacity
            slot.status = status

            db.session.add(slot)
            db.session.commit()
            return ("Slot created")
    
    exams = current_user.examiner.exams
    return render_template("examiner_exams.html", exams=exams, exam=exam)


@app.route("/examiner/slots", methods=["GET","POST"])
@roles_required("examiner")
def examiner_slots():
    examiner = current_user.examiner
    edit_id = request.args.get("edit_id")
    edit_slot = Slot.query.get(edit_id) if edit_id else None

    if request.method == "POST":
        st = datetime.fromisoformat(request.form.get("st"))
        et = datetime.fromisoformat(request.form.get("et"))
        capacity = request.form.get("capacity", type=int)
        status = request.form.get("status")

        overlap = Slot.query.filter(Slot.examiner_id==current_user.examiner.id, Slot.st < st, Slot.et > st).first()

        if overlap:
            return "You already has slot at this time !!"
        else:
            slot = edit_slot
            slot.st = st
            slot.et = et
            if edit_slot and edit_slot.capacity != capacity:
                slot.avl_seat += capacity - edit_slot.capacity
            slot.capacity = capacity
            if not edit_slot:
                slot.avl_seat = capacity
            slot.status = status

            db.session.commit()
            return ("Slot updated")

    slots = examiner.slots
    search = request.args.get("search","")
    if search:
        result = Slot.query.join(Slot.exam).join(Exam.course).join(Examiner.user).filter(or_(
            Exam.name.ilike(f"%{search}%"),
            Course.name.ilike(f"%{search}%"),
            Slot.status.ilike(f"%{search}%"),
            User.username.ilike(f"%{search}%")
        )).all()

        if search.isdigit():
            result = Slot.query.filter_by(id=search).all()
        slots = result
    return render_template("examiner_slots.html", slots=slots, edit_slot=edit_slot, search=search)

@app.route("/examiner/delete_slot")
def delete_slot_by_examiner():
    id = request.args.get("slot_id")
    slot = Slot.query.get(id)
    if Booking.query.filter_by(slot_id = id).first():
        return "You already got booking, so can't delete this slot !!"
    else:
        db.session.delete(slot)
        db.session.commit()
        return "Slot deleted"

@app.route("/examiner/bookings")
@roles_required("examiner")
def booked_students():
    examiner = current_user.examiner
    slots = examiner.slots
    booking_list = []
    students = []
    for slot in slots:
        booking_list.extend(slot.bookings)
    for book in booking_list:
        students.append(book.student)
    return render_template("examiner_bookings.html", students=len(students), booking_list=booking_list)

@app.route("/examiner/pending/evaluation")
@roles_required("examiner")
def examiner_evals():
    examiner = current_user.examiner
    slots = examiner.slots
    bookings = []
    for slot in slots:
        for book in slot.bookings:
            if book.status == "Completed":
                bookings.append(book)
    return render_template("examiner_evals.html", bookings=bookings)

@app.route("/examiner/evaluate", methods=["GET","POST"])
@roles_required("examiner")
def examiner_evaluate():
    examiner = current_user.examiner
    book_id = request.args.get("book_id")
    book = Booking.query.get(book_id)
    if request.method == "POST":
        remarks = request.form.get("remarks") or "NA"
        total = 0
        for rubric in book.slot.exam.rubrics:
            score = request.form.get(f"marks_{rubric.id}", 0)
            total += rubric.weightage*int(score)/100
        eval = Evaluation(booking_id=book.id, student_id=book.student_id, examiner_id=examiner.id,
                          remarks=remarks, marks_got=total)
        db.session.add(eval)
        book.status = "Evaluated"
        db.session.commit()
        return "Evaluation Successful !!"
    return render_template("examiner_evaluate.html", book=book)


# ----------------- Student Functionality --------------------------------------------------------------------
from datetime import timedelta
@app.route("/student/dashboard")
@roles_required("student")
def student_dashboard():
    student = current_user.student
    exam_count = Exam.query.filter_by(status="Booking Open").count()
    booking_count = Booking.query.filter_by(student_id=student.id).count()
    upcoming_bookings = Booking.query.join(Booking.slot).filter(
        Booking.student_id==student.id, Booking.status=="Booked", Slot.st > datetime.now()).all()
    result_count = Evaluation.query.filter(Evaluation.student_id==student.id).count()

    recent_bookings = Booking.query.filter(Booking.student_id==student.id, Booking.date > (datetime.now() - timedelta(days=7))).all()

    recent_results = Evaluation.query.filter(
        Evaluation.student_id==student.id, Evaluation.eval_date > (datetime.now() - timedelta(days=7))).all()
    return render_template("student_dashboard.html", exam_count=exam_count, booking_count=booking_count,
                           upcoming_bookings=upcoming_bookings, result_count=result_count, recent_bookings=recent_bookings,
                           recent_results=recent_results)

@app.route("/student/examinations")
def student_exams():
    exams = Exam.query.filter_by(status="Booking Open").all()
    return render_template("student_exams.html", exams=exams)

@app.route("/student/slots")
def student_exam_slots():
    exam_id = request.args.get("exam_id")
    exam = Exam.query.get(exam_id)
    slots = Slot.query.filter_by(status="Booking Open", exam_id=exam.id).all()
    return render_template("student_exam_slots.html", exam=exam, slots=slots)

@app.route("/student/slot_booking")
@roles_required("student")
def book_slot():
    student = current_user.student
    exam_id = request.args.get("exam_id")
    slot_id = request.args.get("slot_id")
    book = Booking(student_id=student.id, slot_id=slot_id)
    db.session.add(book)
    slot = Slot.query.get(slot_id)
    slot.avl_seat -= 1
    db.session.commit()
    return redirect(url_for("student_exam_slots", exam_id=exam_id))

@app.route("/student/booking/update")
def student_booking_update():
    book_id = request.args.get("book_id")
    action = request.args.get("action")
    book = Booking.query.get(book_id)
    if action == "cancel":
        if book.status == "Booked" and book.slot.exam.sbed >= date.today():
            book.status = "Cancelled"
            db.session.commit()
            return "Booking Cancelled !!"
        else:
            return "Slot booking has ended, so can't cancel this booking !!"
    else:
        if book.status == "Booked" and book.slot.et > datetime.now():
            book.status = "Completed"
            db.session.commit()
            return "You have attempt you exam !!"
        else:
            book.status = "Cancelled"
            db.session.commit()
            return "You have missed your exam !!"


@app.route("/student/bookings")
@roles_required("student")
def student_booking_history():
    student = current_user.student
    bookings = student.bookings
    return render_template("student_bookings.html", bookings=bookings)


@app.route("/student/results")
@roles_required("student")
def student_results():
    student = current_user.student
    results = Evaluation.query.filter(Evaluation.student_id==student.id).all()
    return render_template("student_results.html", results=results)


from flask import send_file
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
@app.route("/download/scorecard")
@roles_required("student")
def download_scorecard():
    student = current_user.student
    eval_id = request.args.get("eval_id")
    eval = Evaluation.query.get(eval_id)
    buffer = BytesIO()
    pdf = SimpleDocTemplate(buffer)
    style = getSampleStyleSheet()
    story = [Paragraph("Examination Scorecard", style["Title"])]
    details = [
        ["Student Name", current_user.username, "Student Id", current_user.email],
        ["Course", eval.booking.slot.exam.course.name,"Course code", eval.booking.slot.exam.course.code],
        ["Examination", eval.booking.slot.exam.name, "Exam Type", eval.booking.slot.exam.type],
        ["Max Marks", str(eval.booking.slot.exam.max_marks), "Result published", str(eval.eval_date.strftime("%d %b %Y"))]
    ]
    details_table = Table([[Paragraph(value, style["BodyText"]) for value in row] for row in details])
    details_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,3), colors.HexColor("#d7d0d0")),
        ("BACKGROUND", (2,0), (3,3), colors.HexColor("#d7d0d0")),
        ("LEFTPADDING", (0,0), (3,3), 6),
        ("RIGHTPADDING", (0,0), (3,3), 6),
        ("TOPPADDING", (0,0), (3,3), 7),
        ("BOTTOMPADDING", (0,0), (3,3), 7)
    ])) # (column, row)
    story += [details_table,
            Paragraph(f"Marks Obtained: {eval.marks_got}/{eval.booking.slot.exam.max_marks}", style["Heading2"]),
            Paragraph(F"Remarks: {eval.remarks}", style["Heading2"])
        ]
    pdf.build(story)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="Scorecard.pdf")


import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
@app.route("/admin/statistics")
def statistics():
    x_axis = ["One","TWO","THREE","Four"]
    y_axis = [2,3,4,10]
    plt.bar(x_axis, y_axis)
    plt.savefig('static/bar.png')
    plt.close()

    plt.pie(y_axis, labels=x_axis, shadow=True)
    plt.savefig("static/pie.png")
    plt.close()
    return render_template("statistics.html")


# ============================================================
# ADVANCED EXAMINATION ANALYTICS AND PERFORMANCE REPORT
# ============================================================

from collections import defaultdict


def calculate_percentage(obtained, maximum):
    """
    Calculate percentage safely.

    Returns 0 when maximum marks are not available.
    """
    if maximum is None or maximum <= 0:
        return 0

    return round((obtained / maximum) * 100, 2)


def get_exam_booking_statistics(exam):
    """
    Generate booking statistics for one examination.
    """

    total_slots = len(exam.slot)
    total_capacity = 0
    available_seats = 0
    total_bookings = 0
    completed_bookings = 0
    evaluated_bookings = 0
    pending_evaluations = 0

    unique_students = set()
    total_marks = 0
    evaluation_count = 0
    passed_students = 0
    failed_students = 0

    for slot in exam.slot:

        capacity = slot.capacity or 0
        available = slot.avl_seat or 0

        total_capacity += capacity
        available_seats += available

        for booking in slot.bookings:

            if booking.status == "Cancelled":
                continue

            total_bookings += 1
            unique_students.add(booking.student_id)

            if booking.status in ["Completed", "Evaluated"]:
                completed_bookings += 1

            evaluation = booking.eval

            if evaluation:

                evaluated_bookings += 1

                marks = evaluation.marks_got or 0
                maximum = exam.max_marks or 0

                total_marks += marks
                evaluation_count += 1

                percentage = calculate_percentage(
                    marks,
                    maximum
                )

                # Pass criteria: 40% of maximum marks.
                # Change this value if your institution
                # follows a different passing percentage.
                if percentage >= 40:
                    passed_students += 1
                else:
                    failed_students += 1

            elif booking.status == "Completed":
                pending_evaluations += 1

    average_marks = 0

    if evaluation_count > 0:
        average_marks = round(
            total_marks / evaluation_count,
            2
        )

    occupancy_percentage = 0

    if total_capacity > 0:
        occupied_seats = max(
            0,
            total_capacity - available_seats
        )

        occupancy_percentage = round(
            (occupied_seats / total_capacity) * 100,
            2
        )

    return {
        "total_slots": total_slots,
        "total_capacity": total_capacity,
        "available_seats": available_seats,
        "total_bookings": total_bookings,
        "total_students": len(unique_students),
        "completed_bookings": completed_bookings,
        "evaluated_bookings": evaluated_bookings,
        "pending_evaluations": pending_evaluations,
        "average_marks": average_marks,
        "passed_students": passed_students,
        "failed_students": failed_students,
        "occupancy_percentage": occupancy_percentage
    }


# ------------------------------------------------------------
# ADMIN: COMPLETE EXAMINATION PERFORMANCE REPORT
# ------------------------------------------------------------

@app.route(
    "/admin/reports/exam-performance",
    methods=["GET"]
)
@roles_required("admin")
def admin_exam_performance_report():

    exams = Exam.query.order_by(Exam.id.desc()).all()

    report_data = []

    overall_statistics = {
        "total_examinations": len(exams),
        "total_students": 0,
        "total_bookings": 0,
        "total_evaluations": 0,
        "total_pending_evaluations": 0,
        "total_passed_students": 0,
        "total_failed_students": 0
    }

    for exam in exams:

        statistics = get_exam_booking_statistics(exam)

        exam_report = {
            "exam_id": exam.id,
            "exam_name": exam.name,
            "exam_type": exam.type,
            "course_name": (
                exam.course.name if exam.course else "N/A"
            ),
            "maximum_marks": exam.max_marks or 0,
            "exam_status": exam.status,
            "statistics": statistics
        }

        report_data.append(exam_report)

        overall_statistics["total_students"] += (
            statistics["total_students"]
        )

        overall_statistics["total_bookings"] += (
            statistics["total_bookings"]
        )

        overall_statistics["total_evaluations"] += (
            statistics["evaluated_bookings"]
        )

        overall_statistics["total_pending_evaluations"] += (
            statistics["pending_evaluations"]
        )

        overall_statistics["total_passed_students"] += (
            statistics["passed_students"]
        )

        overall_statistics["total_failed_students"] += (
            statistics["failed_students"]
        )

    return jsonify({
        "success": True,
        "message": "Examination performance report generated successfully.",
        "overall_statistics": overall_statistics,
        "examinations": report_data
    })


# ------------------------------------------------------------
# ADMIN: SLOT UTILIZATION REPORT
# ------------------------------------------------------------

@app.route(
    "/admin/reports/slot-utilization",
    methods=["GET"]
)
@roles_required("admin")
def admin_slot_utilization_report():

    slots = Slot.query.order_by(Slot.id.desc()).all()

    slot_reports = []

    total_capacity = 0
    total_available = 0
    total_occupied = 0

    for slot in slots:

        capacity = slot.capacity or 0
        available = slot.avl_seat or 0

        occupied = max(0, capacity - available)

        if capacity > 0:
            utilization = round(
                (occupied / capacity) * 100,
                2
            )
        else:
            utilization = 0

        total_capacity += capacity
        total_available += available
        total_occupied += occupied

        exam_name = (
            slot.exam.name if slot.exam else "N/A"
        )

        examiner_name = "Not Assigned"

        if slot.examiner and slot.examiner.user:
            examiner_name = (
                slot.examiner.user.username or "Not Assigned"
            )

        slot_reports.append({
            "slot_id": slot.id,
            "exam_name": exam_name,
            "examiner_name": examiner_name,
            "start_time": (
                slot.st.isoformat() if slot.st else None
            ),
            "end_time": (
                slot.et.isoformat() if slot.et else None
            ),
            "capacity": capacity,
            "available_seats": available,
            "occupied_seats": occupied,
            "utilization_percentage": utilization,
            "status": slot.status
        })

    overall_utilization = 0

    if total_capacity > 0:
        overall_utilization = round(
            (total_occupied / total_capacity) * 100,
            2
        )

    return jsonify({
        "success": True,
        "message": "Slot utilization report generated successfully.",
        "summary": {
            "total_slots": len(slots),
            "total_capacity": total_capacity,
            "total_occupied_seats": total_occupied,
            "total_available_seats": total_available,
            "overall_utilization": overall_utilization
        },
        "slots": slot_reports
    })


# ------------------------------------------------------------
# EXAMINER: PERSONAL EVALUATION PERFORMANCE REPORT
# ------------------------------------------------------------

@app.route(
    "/examiner/reports/performance",
    methods=["GET"]
)
@roles_required("examiner")
def examiner_performance_report():

    examiner = current_user.examiner

    if not examiner:
        return jsonify({
            "success": False,
            "message": "Examiner profile not found."
        }), 404

    evaluations = Evaluation.query.filter_by(
        examiner_id=examiner.id
    ).all()

    total_evaluations = len(evaluations)
    total_marks = 0
    highest_marks = 0
    lowest_marks = None

    exam_summary = defaultdict(
        lambda: {
            "exam_name": "",
            "total_evaluations": 0,
            "total_marks": 0,
            "average_marks": 0
        }
    )

    for evaluation in evaluations:

        marks = evaluation.marks_got or 0

        total_marks += marks

        highest_marks = max(
            highest_marks,
            marks
        )

        if lowest_marks is None:
            lowest_marks = marks
        else:
            lowest_marks = min(
                lowest_marks,
                marks
            )

        booking = evaluation.booking

        if booking and booking.slot and booking.slot.exam:

            exam = booking.slot.exam

            item = exam_summary[exam.id]

            item["exam_name"] = exam.name
            item["total_evaluations"] += 1
            item["total_marks"] += marks

    for exam_id, item in exam_summary.items():

        count = item["total_evaluations"]

        if count > 0:
            item["average_marks"] = round(
                item["total_marks"] / count,
                2
            )

    average_marks = 0

    if total_evaluations > 0:
        average_marks = round(
            total_marks / total_evaluations,
            2
        )

    assigned_exams = Exam.query.filter_by(
        examiner_id=examiner.id
    ).count()

    return jsonify({
        "success": True,
        "examiner": {
            "id": examiner.id,
            "name": (
                examiner.user.username
                if examiner.user else "N/A"
            ),
            "department": examiner.department
        },
        "performance": {
            "assigned_examinations": assigned_exams,
            "total_evaluations": total_evaluations,
            "average_marks_given": average_marks,
            "highest_marks_given": highest_marks,
            "lowest_marks_given": (
                lowest_marks if lowest_marks is not None else 0
            )
        },
        "exam_wise_summary": list(
            exam_summary.values()
        )
    })




























