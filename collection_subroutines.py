import sys
sys.path.insert(0, 'libs')
import re
import datetime
import time
import hashlib
import string
import random

from pytz import timezone
import pytz

import logging

import urllib
import requests
from bs4 import BeautifulSoup

from models import *




def get_connection():
    """ Connect to enrollware and get cookies"""
    sess = requests.Session()

    payload = {'__LASTFOCUS' : '',
               '__VIEWSTATE' : '/wEPDwULLTE3MTA1ODgwNDRkGAEFHl9fQ29udHJvbHNSZXF1aXJlUG9zdEJhY2tLZXlfXxYBBQpyZW1lbWJlck1l',
               '__EVENTTARGET' : '',
               '__EVENTARGUMENT' : '',
               'username' : 'paul',
               'password' : 'XXXXXXXXXXXX',
               'rememberMe' : 'on',
               'loginButton' : 'Sign In'
                }
    
    login_url = 'https://enrollware.com/admin/login.aspx?ReturnUrl=/admin/'
    
    response = sess.post(login_url, data=(payload))

    return response




def get_past_class_list(days_into_past):
    """Get a list of the past classes"""

    response = get_connection()

    sess = requests.Session()

    class_url = 'https://www.enrollware.com/admin/past-classes.aspx'

    response2 = sess.get(class_url, cookies=response.cookies)

    return parse_list_of_classes(response2, days_from_now = days_into_past)




def get_upcoming_class_list(days_into_future):
    """Get a list of upcomming classes."""
    response = get_connection()

    return parse_list_of_classes(response, days_from_now = days_into_future)



def insert_enrollments(class_keys):

    class_id_list = []

    for class_key in class_keys:
        class_id_list.append(class_key.name())

    # on average we are looking at 150 class ids for the past day and future 30 days.
    # to rememdy this, pull out ten ids at a time, anaylze them, then add those to a checked
    # db table. If there are no classes not checked (all classes checked), then clear the 
    # checked table

    response = get_connection()

    classes_checked = 0
    for class_id in class_id_list:

        if classes_checked > 9:
            break

        if ClassesChecked.get_by_key_name(class_id) is None:

            logging.info('Checking class enrollment - class id: ' + str(class_id))
            
            class_enrollment_data = get_class_students(response, class_id)
            
            for enrollment_record in class_enrollment_data:
                # [name_hash, email, reg_date_time, phone, phone_hash, cert_type, ew_enrollment_record_id]
                student_key_name = enrollment_record[0] + enrollment_record[4]

                if Student.get_by_key_name(student_key_name) is None:

                    Student(key_name = student_key_name,
                        phone = enrollment_record[3],
                        email_domain = enrollment_record[1],
                        zip_code = '0').put()

                enrollment_key_name = class_id + student_key_name

                if Enrollment.get_by_key_name(enrollment_key_name) is None:

                    """class_key_name + student_key_name"""
                    Enrollment(key_name = enrollment_key_name,
                        enrollment_date_time = enrollment_record[2],
                        student_key_name = student_key_name,
                        class_key_name = class_id,
                        certification_type = enrollment_record[5],
                        ew_enrollment_record_id = enrollment_record[6],
                        test_score = 0).put()

            ClassesChecked(key_name = class_id).put()

            classes_checked = classes_checked + 1

    """ if number of classes checked is not 10, dump entire classes checked table """
    if classes_checked is not 10:
        time.sleep(1) # give time for last ClassesChecked put() to register.
        empty_classes_checked_relation()



def parse_list_of_classes(response_obj, days_from_now = 30):
    """Takes a page's response object and returns a list of class params"""
    bs_content = BeautifulSoup(response_obj.text)

    class_list = []

    for tr in bs_content.tbody.find_all('tr'):
        
        td = tr.find_all('td')

        """Parse class name"""
        if td[1].string is not None:
            db_class_name = td[1].string.strip(None)
        else:
            continue

        """Parse Time"""
        if td[0].string is None:
            continue
        else: 
            
            date_time_str = td[0].string.strip(None) + "m"

            dt_struct = datetime.datetime.strptime(date_time_str, "%a %m/%d/%y %I:%M%p")

            db_class_date_time = timezone('US/Eastern').localize(dt_struct)

            """ Break if date of class is more than a month out from the check time """
            time_till_class = db_class_date_time - datetime.datetime.now(pytz.utc)
            
            if abs(time_till_class.days) > days_from_now:
                break

        """Parse location"""
        db_location= td[2].string.strip(None)
        if not db_location:
            db_location = 'Invalid' 

        """Parse Instructor"""
        db_instructor = td[3].string.strip(None)
        if not db_instructor:
            continue

        """Parse Enrollment"""
        if td[4].string is not None:       
            enrollment = td[4].string.strip(None)
            if "+" in enrollment:
                enroll_re_obj = re.match('(.+)\+(.+) / (.+)', enrollment)
                db_enrollment_cap = int(enroll_re_obj.group(3))
            else:
                enroll_re_obj = re.match('(.+) / (.+)', enrollment)
                db_enrollment_cap = int(enroll_re_obj.group(2))
        else:
            db_enrollment_cap = 0

        """Get Enrolware's class id"""
        if td[5] is not None:
            db_ew_class_id = re.search('id=(\d+)', str(td[5])).group(1)
        else:
            continue

        class_list.append([db_ew_class_id,
                db_class_date_time,
                db_class_name,
                db_location, 
                db_instructor, 
                db_enrollment_cap])

    return class_list



def get_class_students(response, class_id):
    """Get class-specific info page"""

    sess = requests.Session()

    class_url = 'https://www.enrollware.com/admin/class-edit.aspx?id=' + str(class_id)

    response2 = sess.get(class_url, cookies=response.cookies)

    html_content = BeautifulSoup(response2.text)

    mainContent_studentPanel = BeautifulSoup(str(html_content.find_all(id='mainContent_studentPanel')))

    tbody = BeautifulSoup(str(mainContent_studentPanel.find_all('tbody')))

    tr_list = tbody.find_all('tr')

    class_students = []

    for tr in tr_list:

        td = tr.find_all('td')

        """Parse out student name"""
        if td[1].contents[0]:
            name = td[1].contents[0].string.strip(None)
            if not name:
                name = str(td[1].contents[1].string).strip(None)

        if not name or name == ',':
            continue

        name_list = name.split(',') 

        name = name_list[0] + ", " + name_list[1].strip(None)
        
        m = hashlib.md5()
        m.update(name)
        name_hash = m.hexdigest()

        """Parse out email address"""
        email = ''
        for content in td[1].contents:
            content_string = content.string

            if content_string is None:
                continue

            content_string = content_string.strip(None)

            if not content_string:
                continue

            if string.find(content_string, '@') > -1:
                email = content_string.split('@')[1]
                break
        
        if not email:
            continue

        """Parse registration date time"""
        reg_date = td[4].contents[0].string.strip(None)
        reg_time =  td[4].contents[3].string.strip(None)

        """04/10/2013 12:15pm"""
        dt_struct = datetime.datetime.strptime(reg_date + " " + reg_time, "%m/%d/%Y %I:%M%p")
        reg_date_time = timezone('US/Eastern').localize(dt_struct)

        """Parse out Phone #"""
        phone_str = td[6].string.strip(None)

        m = hashlib.md5()
        m.update(phone_str)
        phone_hash = m.hexdigest()

        phone_obj = phone_str.split('-')

        try:
            phone = int(phone_obj[0] + phone_obj[1])
        except:
            logging.info('Skipping student due to invalid phone #')
            continue

        """Parse out Cert Type"""
        cert_type_str = str(td[7].string)

        if string.find(cert_type_str.lower(), 'cert') > -1:
            cert_type = cert_type_str
            ew_enrollment_td_index = 8
        else:
            cert_type = None
            ew_enrollment_td_index = 7

        """Parse out ew enrollment id"""
        ew_enrollment_record_url = td[ew_enrollment_td_index].a['href']
        ew_enrollment_record_id = re.search('aspx\?id=(\d+)&', ew_enrollment_record_url).group(1)

        class_students.append([name_hash, email, reg_date_time, phone, phone_hash, cert_type, ew_enrollment_record_id])

    return class_students



def empty_classes_checked_relation():
    
    query = ClassesChecked.all()
    entries = query.fetch(500)

    if len(entries) == 0:
        logging.info('ClassesChecked relation empty.')
        return True
    
    else:
        logging.info('Deleting chunk of classes checked relation.')
        db.delete(entries)
        time.sleep(1) # give time for db.delete() to register.
        empty_classes_checked_relation()



def empty_grades_checked_relation():
    
    query = GradesChecked.all()
    entries = query.fetch(500)

    if len(entries) == 0:
        logging.info('GradesChecked relation empty.')
        return True
    
    else:
        logging.info('Deleting chunk of grades checked relation.')
        db.delete(entries)
        time.sleep(1) # give time for db.delete() to register.
        empty_grades_checked_relation()


def get_enrollment(offset):

    # get enrollment
    e = Enrollment.all()
    e.filter('test_score = ', 0)
    enrollment = e.get(offset = offset)

    if enrollment is None:
        return None

    # see if it is in grades checked
    if GradesChecked.get_by_key_name(enrollment.key().name()) is None:
        return enrollment
    else:
        return get_enrollment(offset + 1)




def parse_student_enrollment(response, ew_enrollment_record_id):
    """Get the enrollment data for a particular student-class entity."""
    """Return zip code and grade in class"""

    sess = requests.Session()

    enrollment_url = 'https://www.enrollware.com/admin/classRegistrationEdit.aspx?id=' + ew_enrollment_record_id

    response2 = sess.get(enrollment_url, cookies=response.cookies)

    html_content = BeautifulSoup(response2.text)

    try:
        zip_code = html_content.find("input", {"id": "mainContent_ZipTextBox"})['value']
    except:
        zip_code = '0'

    try:
        class_name_str = html_content.find("span", {"id": "mainContent_className"}).string
    except:
        logging.error('No class name found for ew enrollment id ' + ew_enrollment_record_id)
        class_name_str = ''

    grade_remediated_list = [0, None]

    try:
        grade_str = html_content.find("input", {"id": "mainContent_testScore"})['value']
    except:
        grade_str = ''    

    grade_re_obj = re.match('(\d+)(\D*)', grade_str)

    grade = 0
    remediated = None
    if grade_re_obj is not None:
        grade = int(grade_re_obj.group(1))
        remediated = grade_re_obj.group(2)

    if remediated is not None:
        if remediated.find('R') > -1:
            remediated = True
        else:
            remediated = False

    return [zip_code, grade, remediated]




def get_random_past_class_id_list(length_of_list):
    """Get a random list of past class ids."""
    response = get_connection()

    sess = requests.Session()

    class_url = 'https://www.enrollware.com/admin/past-classes.aspx'

    response2 = sess.get(class_url, cookies=response.cookies)

    html_content = BeautifulSoup(response2.text)

    class_id_list = []

    for tr in html_content.tbody.find_all('tr'):
            
        td = tr.find_all('td')

        """Get Enrolware's class id"""
        if td[5] is not None:
            ew_class_id = re.search('id=(\d+)', str(td[5])).group(1)
        else:
            continue

        class_id_list.append(ew_class_id)

    random_class_id_list = []

    for i in range(length_of_list):
        random_class_id_list.append(class_id_list[random.randint(0,len(class_id_list)-1)])

    return random_class_id_list



def get_random_upcoming_class_id_list(length_of_list):
    """Get random list of enrollware class ids. Only used for testing."""
    response = get_connection()

    html_content = get_class_list(response)

    class_id_list = []

    for tr in html_content.tbody.find_all('tr'):
            
        td = tr.find_all('td')

        """Get Enrolware's class id"""
        if td[5] is not None:
            ew_class_id = re.search('id=(\d+)', str(td[5])).group(1)
        else:
            continue

        class_id_list.append(ew_class_id)

    random_class_id_list = []

    for i in range(length_of_list):
        random_class_id_list.append(class_id_list[random.randint(0,len(class_id_list)-1)])

    return random_class_id_list