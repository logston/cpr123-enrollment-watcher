import sys
sys.path.insert(0, 'libs')
import datetime
import time

from pytz import timezone
import pytz

import webapp2
import logging
from google.appengine.ext import db

from models import *
from collection_subroutines import *


class CollectPastClasses(webapp2.RequestHandler):
    def get(self):
        """Sign in and grab list of past classes."""

        for class_obj in get_past_class_list(30):

            """   Insert class if it doesn't exist """
            if Class.get_by_key_name(class_obj[0]) is None:
                Class(key_name = class_obj[0],
                    date_time = class_obj[1],
                    name = class_obj[2],
                    location = class_obj[3],
                    instructor = class_obj[4],
                    enrollment_cap = class_obj[5]).put()


class CollectUpcomingClasses(webapp2.RequestHandler):
    def get(self):
        """Sign in and grab list of classes to come."""

        for class_obj in get_upcoming_class_list(30):

            """   Insert class if it doesn't exist """
            if Class.get_by_key_name(class_obj[0]) is None:
                Class(key_name = class_obj[0],
                    date_time = class_obj[1],
                    name = class_obj[2],
                    location = class_obj[3],
                    instructor = class_obj[4],
                    enrollment_cap = class_obj[5]).put()



class CollectAllClasses(webapp2.RequestHandler):
    def get(self):
        """Sign in and grab list of classes within plus or minus 30 days"""

        for class_obj in get_past_class_list(30):

            """   Insert class if it doesn't exist """
            if Class.get_by_key_name(class_obj[0]) is None:
                Class(key_name = class_obj[0],
                    date_time = class_obj[1],
                    name = class_obj[2],
                    location = class_obj[3],
                    instructor = class_obj[4],
                    enrollment_cap = class_obj[5]).put()

        for class_obj in get_upcoming_class_list(30):

            """   Insert class if it doesn't exist """
            if Class.get_by_key_name(class_obj[0]) is None:
                Class(key_name = class_obj[0],
                    date_time = class_obj[1],
                    name = class_obj[2],
                    location = class_obj[3],
                    instructor = class_obj[4],
                    enrollment_cap = class_obj[5]).put()



class CollectPastEnrollments(webapp2.RequestHandler):
    def get(self):
        """Grab any new enrollments for classes prior to yesterday."""

        dt_yesterday = datetime.datetime.now(pytz.utc) - datetime.timedelta(days=1)

        class_keys = db.GqlQuery("SELECT __key__ FROM Class WHERE date_time <= :1", dt_yesterday)

        insert_enrollments(class_keys)




class CollectEnrollments(webapp2.RequestHandler):
    def get(self):
        """Grab any enrollments in the past 24 hours and forward."""

        dt_yesterday = datetime.datetime.now(pytz.utc) - datetime.timedelta(days=1)

        class_keys = db.GqlQuery("SELECT __key__ FROM Class WHERE date_time > :1", dt_yesterday)

        insert_enrollments(class_keys)



class CollectZipCodes(webapp2.RequestHandler):
    def get(self):
        """Grab zip codes for students who don't have them in their record."""

        response = get_connection()

        # get list of students with no zip code
        s = Student.all()
        s.filter('zip_code =', '0')
        student_list = s.fetch(10)

        for student in student_list:
            e = Enrollment.all()
            e.filter('student_key_name = ', student.key().name())
            
            try:
                ew_enrollment_record_id = e.get().ew_enrollment_record_id
            except:
                logging.error('Ew enrollment record id not found - \
                    Student key_name: ' + student.key().name())
                continue

            enrollment_data = parse_student_enrollment(response, ew_enrollment_record_id)

            student.zip_code = enrollment_data[0]

            try:
                student.put()
            except:
                logging.error('Failed zip code update - Student key name: ' + student.key().name())



class CollectAllCurrentGrades(webapp2.RequestHandler):
    def get(self):
        """Grab grades for enrollments that don't have grades in their record."""
        
        response = get_connection()

        grades_checked = 0
        while True:
            if grades_checked > 9:
                break

            enrollment = get_enrollment(0)

            if enrollment is None:
                break

            if GradesChecked.get_by_key_name(enrollment.key().name()) is None:
            
                ew_enrollment_record_id = enrollment.ew_enrollment_record_id

                enrollment_data = parse_student_enrollment(response, ew_enrollment_record_id)

                enrollment.test_score = enrollment_data[1]

                enrollment.remediated = enrollment_data[2]

                logging.info('Updating enrollment - id: ' + ew_enrollment_record_id)
                logging.info('grade: ' + str(enrollment_data[1]))
                logging.info('remediation: ' + str(enrollment_data[2]))
                logging.info('...')

                try:
                    enrollment.put()
                    logging.info('success.')
                except:
                    logging.error('failed.')

                GradesChecked(key_name=enrollment.key().name()).put()

            grades_checked = grades_checked + 1

        """ if number of grades checked is not 10, dump entire classes checked table """
        if grades_checked is not 10:
            time.sleep(1) # give time for last ClassesChecked put() to register.
            empty_grades_checked_relation()

