import sys
import os
sys.path.insert(0, 'libs')
import re
import time
import datetime
import urllib


import webapp2
import datetime
from google.appengine.ext import db

from bs4 import BeautifulSoup
import requests
import logging
import jinja2





jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__) + "/templates"))

class Class(db.Model):
    """Model for each class."""
    class_date_time = db.DateTimeProperty(required=True)
    class_name = db.StringProperty(required=True)
    location = db.StringProperty(required=True)
    instructor = db.StringProperty(required=True)
    enrollment_cap = db.IntegerProperty(required=True)

class ClassEnrollment(db.Model):
    collect_time = db.DateTimeProperty(auto_now_add=True, required=True)
    enrollment_primary = db.IntegerProperty(required=True)
    enrollment_secondary = db.IntegerProperty()


class CollectClassData(webapp2.RequestHandler):
    def get(self):
        """Sign in and grab list of classes to come."""

        payload = {'__LASTFOCUS' : '',
                   '__VIEWSTATE' : '/wEPDwULLTE3MTA1ODgwNDRkGAEFHl9fQ29udHJvbHNSZXF1aXJlUG9zdEJhY2tLZXlfXxYBBQpyZW1lbWJlck1l',
                   '__EVENTTARGET' : '',
                   '__EVENTARGUMENT' : '',
                   'username' : 'XXXXXXXXXXX',
                   'password' : 'XXXXXXXXXXX',
                   'rememberMe' : 'on',
                   'loginButton' : 'Sign In'
                    }
        
        url = 'https://enrollware.com/admin/login.aspx?ReturnUrl=/admin/'
        
        response = requests.post(url, data=(payload))

        soup = BeautifulSoup(response.text)

        class_list = []

        for tr in soup.tbody.find_all('tr'):
            
            td = tr.find_all('td')

            """Parse Time"""
            if td[0].string is not None:
                date_time = td[0].string.strip(' \t\n\r')
                dt_re_obj = re.match('(...).(.+)/(..)/(..).(.+):(..)(.)', date_time)

                if dt_re_obj.group(7) == 'p':
                    dtampm = "PM"
                else:
                    dtampm = "AM"
                
                dt_str = "%s/%s/%s %s:%s %s" % (dt_re_obj.group(2), 
                    dt_re_obj.group(3), 
                    dt_re_obj.group(4), 
                    dt_re_obj.group(5), 
                    dt_re_obj.group(6),
                    dtampm)

                dt_struct = time.strptime(dt_str, "%m/%d/%y %I:%M %p")
                db_class_date_time = datetime.datetime.fromtimestamp(time.mktime(dt_struct))
            else:
                db_class_date_time = datetime.datetime.fromtimestamp(0)

            days_till = (time.mktime(dt_struct) - time.time()) / (60 * 60 * 24)


            if td[1].string is not None:
                db_class_name = td[1].string.strip(' \t\n\r')
            else:
                db_class_name = 'Invalid'

            if db_class_name is 'Invalid':
                continue

            
            if td[2].string is not None:
                db_location= td[2].string.strip(' \t\n\r')
            else:
                db_location = 'Invalid' 

            db_instructor = td[3].string.strip(' \t\n\r')
            if not db_instructor:
                db_instructor = 'Invalid'


            """Parse Enrollment"""
            if td[4].string is not None:       
                enrollment = td[4].string.strip(' \t\n\r')
                if "+" in enrollment:
                    enroll_re_obj = re.match('(.+)\+(.+) / (.+)', enrollment)
                    db_enrollment_primary = int(enroll_re_obj.group(1))
                    db_enrollment_secondary = int(enroll_re_obj.group(2))
                    db_enrollment_cap = int(enroll_re_obj.group(3))
                else:
                    enroll_re_obj = re.match('(.+) / (.+)', enrollment)
                    db_enrollment_primary = int(enroll_re_obj.group(1))
                    db_enrollment_secondary = 0
                    db_enrollment_cap = int(enroll_re_obj.group(2))

            db_key = urllib.quote_plus(db_class_date_time.isoformat() 
                + db_class_name 
                + db_instructor)


            class_info_dict = {'key_name' : db_key,
            'date_time' : db_class_date_time, 
            'name' : db_class_name, 
            'location' : db_location,
            'instructor' : db_instructor,
            'enrollment_primary' : db_enrollment_primary,
            'enrollment_secondary' : db_enrollment_secondary,
            'enrollment_cap' : db_enrollment_cap
            }

            class_list.append(class_info_dict)

            
            """ Insert class if it doesn't exist """
            if Class.get_by_key_name(db_key) is None:
                Class(key_name = db_key,
                    class_date_time = db_class_date_time,
                    class_name = db_class_name,
                    location = db_location,
                    instructor = db_instructor,
                    enrollment_cap = db_enrollment_cap).put()

            """ Insert enrollment status tuple """
            ClassEnrollment(parent = Class.get_by_key_name(db_key).key(),
                enrollment_primary = db_enrollment_primary,
                enrollment_secondary = db_enrollment_secondary).put()
            

            """ Break if date of class is more than a month out from the check time """
            if days_till > 30:
                break

        template = jinja_environment.get_template('class_list_collected.html')
        self.response.out.write(template.render({'classes':class_list}))



class ClassList(webapp2.RequestHandler):
    def get(self):
        """ Get all the classes in the data store and show them. """

        class_list = []

        for class_obj in Class.all():


            class_info_dict = {'key' : class_obj.key(),
            'date_time' : class_obj.class_date_time, 
            'class_name' : class_obj.class_name, 
            'location' : class_obj.location,
            'instructor' : class_obj.instructor,
            }

            class_list.append(class_info_dict)

        template_values = {
            'classes': class_list,
        }


        template = jinja_environment.get_template('class_list.html')
        self.response.out.write(template.render(template_values))



class ViewClass(webapp2.RequestHandler):
    def get(self):

        class_key = self.request.get('key')

        class_query = Class.all()
        class_query.filter('__key__ =', db.Key(encoded=class_key))
        class_obj = class_query.get()

        class_enroll_objs = ClassEnrollment.all()
        class_enroll_objs.ancestor(db.Key(encoded=class_key))

        template_values = {
            'class_name' : class_obj.class_name,
            'date_time' : class_obj.class_date_time,
            'location' : class_obj.location,
            'instructor' : class_obj.instructor,
            'enrollment_objs' : class_enroll_objs,
            'enrollment_cap' : class_obj.enrollment_cap,
        }


        template = jinja_environment.get_template('view_class.html')
        self.response.out.write(template.render(template_values))


app = webapp2.WSGIApplication([('/', ClassList),
    ('/ViewClass', ViewClass),
    ('/CollectClassData', CollectClassData)], debug=True)
