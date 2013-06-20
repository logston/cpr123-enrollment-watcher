
import sys
sys.path.insert(0, 'libs')
from collections import Counter
from datetime import *

import logging
from google.appengine.ext import db

import pytz

from models import *


def get_progress_stats():
    progress_stats = []

    # get all classes
    query = Class.all()
    class_obj_list = query.fetch(1000)
    class_count = len(class_obj_list)

    progress_stats.append(['Number of Classes Queried', 1000])
    progress_stats.append(['Number of Classes Found', class_count])

    past_class_count = 0
    future_class_count = 0
    utc = pytz.UTC
    for class_obj in class_obj_list:
        class_datetime  = utc.localize(class_obj.date_time)
        if class_datetime > datetime.now(pytz.utc):
            future_class_count = future_class_count + 1
        if class_datetime <= datetime.now(pytz.utc):
            past_class_count = past_class_count + 1

    progress_stats.append(['Number of Past Classes', past_class_count])
    progress_stats.append(['Number of Future Classes', future_class_count])

    # get all the classes that have been checked
    query = ClassesChecked.all()
    classes_checked_obj_list = query.fetch(1000)
    classes_checked_count = len(classes_checked_obj_list)
    classes_checked_percent = round((float(classes_checked_count) / class_count) * 100)

    progress_stats.append(['Percent of Classes Checked for Enrollments', classes_checked_percent])

    # get all enrollments
    query = Enrollment.all()
    enrollment_obj_list = query.fetch(1000)
    enrollment_count = len(enrollment_obj_list)

    progress_stats.append(['Number of Enrollments Queried', 1000])
    progress_stats.append(['Number of Enrollments Found', enrollment_count])

    # count grades checked relation
    query = GradesChecked.all()
    grades_checked_obj_list = query.fetch(1000)
    grades_checked_count = len(grades_checked_obj_list)

    progress_stats.append(['Number of Checked Grades Queried', 1000])
    progress_stats.append(['Number of Checked Grades Found', grades_checked_count])

    # get all enrollment times
    reg_time_list = []
    for enrollment in enrollment_obj_list:
        reg_time_list.append(enrollment.enrollment_date_time)


    # get all the enrollments that have grades
    enrollment_not_graded_count = 0
    for enrollment in enrollment_obj_list:
        if enrollment.test_score == 0:
            enrollment_not_graded_count = enrollment_not_graded_count + 1

    enrollment_not_graded_percent = round((float(enrollment_not_graded_count) / enrollment_count) * 100)

    progress_stats.append(['Percent of Enrollments Not Graded', enrollment_not_graded_percent])

    # compare enrollment date to grade
    data_point_list = []
    query = Enrollment.all()
    query.filter('test_score !=', 0)
    enrollment_graded_obj_list = query.fetch(100)
    for enrollment in enrollment_graded_obj_list:
        class_obj = Class.get_by_key_name(enrollment.class_key_name)
        td = class_obj.date_time - enrollment.enrollment_date_time
        data_point_list.append([round(td.total_seconds() / (24*60*60)), int(enrollment.test_score)])


    return {
        'progress_stats': progress_stats,
        'data_point_list': data_point_list,
    }



def get_progress_stats(info_to_breakdown):
    # get list of zip codes 
    query = Student.all()
    query.filter('zip_code !=', 0)
    student_obj_list = query.fetch(1000)
    zip_code_count = len(student_obj_list)
    zip_code_list = []
    for student in student_obj_list:
        zip_code_list.append(student.zip_code[:5])

    zip_code_dist = Counter(zip_code_list)


    zip_code_dist_percents = []
    for key in zip_code_dist.keys():
        percent = round(float(zip_code_dist[key] * 100) / zip_code_count)
        zip_code_dist_percents.append(["'" + key + "'", percent])

    logging.info(zip_code_dist)

    return {
        'zip_code_dist': zip_code_dist_percents,
    }
