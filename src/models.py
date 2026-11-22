from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

from datetime import date, datetime

from flask_security.models import fsqla
fsqla.FsModels.set_db_info(db)

class Role(db.Model,fsqla.FsRoleMixin):
    pass

class User(db.Model,fsqla.FsUserMixin):
    student = db.relationship("Student", backref="user", uselist=False)
    examiner = db.relationship("Examiner", backref="user", uselist=False)
    
class Student(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey("user.id"), nullable=False)
    department = db.Column(db.String())
    mob = db.Column(db.String())
    @property
    def total_bookings(self):
        """Return the total number of bookings made by a student."""
        return len(self.bookings)

    @property
    def completed_bookings(self):
        """Count completed examination bookings."""
        return sum(
            1 for booking in self.bookings
            if booking.status == "Completed"
        )
    bookings = db.relationship("Booking", backref="student")
        
class Examiner(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey("user.id"), nullable=False)
    mob = db.Column(db.String())
    department = db.Column(db.String())
    status = db.Column(db.String(), default="Pending")         #Active,Pending,Blacklisted
    slots = db.relationship("Slot", backref="examiner")
    evals = db.relationship("Evaluation", backref="examiner")
    exams = db.relationship("Exam", backref="examiner")
    
class Course(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    code = db.Column(db.Integer())
    name = db.Column(db.String())
    description = db.Column(db.String())
    status = db.Column(db.String())    #Active,Delected
    exam = db.relationship("Exam", backref="course")
    
class Exam(db.Model):
    id = db.Column(db.Integer(),primary_key=True)
    course_id = db.Column(db.Integer(), db.ForeignKey("course.id"), nullable=False)
    examiner_id = db.Column(db.Integer(), db.ForeignKey("examiner.id"))
    name = db.Column(db.String())
    type = db.Column(db.String())    #Viva,Practical,Demo, Assessment
    duration = db.Column(db.Integer())
    max_marks = db.Column(db.Integer())
    scsd = db.Column(db.Date())
    sced = db.Column(db.Date())
    sbsd = db.Column(db.Date())
    sbed = db.Column(db.Date())
    status  = db.Column(db.String())      #Draft,Slot Creation,Booking Open,Closed,Completed
    rubric = db.relationship("Rubric", backref="exam")
    slot = db.relationship("Slot", backref="exam")
    
class Rubric(db.Model):
    id = db.Column(db.Integer(),primary_key=True)
    exam_id = db.Column(db.Integer(), db.ForeignKey("exam.id"), nullable=False)
    criteria = db.Column(db.String())
    max_marks =db.Column(db.Integer())
    weightage = db.Column(db.Integer())
    description = db.Column(db.String())
    
class Slot(db.Model):
    id = db.Column(db.Integer(),primary_key=True)
    exam_id = db.Column(db.Integer(), db.ForeignKey("exam.id"), nullable=False)
    examiner_id = db.Column(db.Integer(), db.ForeignKey("examiner.id"))
    st = db.Column(db.DateTime)
    et = db.Column(db.DateTime)
    capacity = db.Column(db.Integer())
    avl_seat = db.Column(db.Integer())
    status = db.Column(db.String())   #Draft,Booking Open,Booking Closed,Completed
    bookings = db.relationship("Booking", backref="slot")
    
class Booking(db.Model):
    id = db.Column(db.Integer(),primary_key=True)
    student_id = db.Column(db.Integer(), db.ForeignKey("student.id"), nullable=False)
    slot_id = db.Column(db.Integer(), db.ForeignKey("slot.id"), nullable=False)
    date = db.Column(db.Date, default=date.today)
    status = db.Column(db.String())  #Booked,Cancelled,Completed,Evaluate
    eval = db.relationship("Evaluation", backref="booking", uselist=False)
    
class Evaluation(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    booking_id = db.Column(db.Integer(), db.ForeignKey("booking.id"), nullable=False)
    student_id = db.Column(db.Integer(), db.ForeignKey("student.id"), nullable=False)
    examiner_id = db.Column(db.Integer(), db.ForeignKey("examiner.id"), nullable=False)
    marks_got = db.Column(db.Integer(), nullable=False)
    remarks = db.Column(db.String(), default="--")
    eval_date = db.Column(db.DateTime, default=datetime.now)