from google.appengine.ext import db

class Class(db.Model):
    """Model for each class."""
    """key_name = enrollware class id"""
    date_time = db.DateTimeProperty(required=True)
    name = db.StringProperty(required=True)
    location = db.StringProperty(required=True)
    instructor = db.StringProperty(required=True)
    enrollment_cap = db.IntegerProperty(required=True)



class Enrollment(db.Model):
    """Model for class enrollments.""" 
    """key_name = class_key_name + student_key_name"""
    enrollment_date_time = db.DateTimeProperty(required=True)
    student_key_name = db.StringProperty()
    class_key_name = db.StringProperty()
    certification_type = db.StringProperty(choices=set(['Cert', 'Recert']))
    ew_enrollment_record_id = db.StringProperty(required=True)
    test_score = db.IntegerProperty()
    remediated = db.BooleanProperty()



class Student(db.Model):
    """Model for student data."""
    """key_name = md5hash('student full name') + md5hash('phone #') """
    phone = db.IntegerProperty()
    email_domain = db.StringProperty()
    zip_code = db.StringProperty()



class ClassesChecked(db.Model):
    """Table of class ids that have been checked for enrollment changes in the past 24hrs."""
    """key_name = enrollware class id"""
    collected = db.DateTimeProperty(required=True, auto_now_add=True)


class GradesChecked(db.Model):
    """Table of enrollment ids that have been checked for grade changes."""
    """key_name = Enrollment key_name"""
    collected = db.DateTimeProperty(required=True, auto_now_add=True)