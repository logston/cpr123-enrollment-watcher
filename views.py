import os

import webapp2

import jinja2

from view_subroutines import *


jinja_environment = jinja2.Environment(autoescape=True,
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))

class ViewProgress(webapp2.RequestHandler):
    def get(self):
        """Show progress by gathering stats from db"""

        template_values = get_progress_stats()

        template = jinja_environment.get_template('progress_stats.html')
        self.response.out.write(template.render(template_values))



class ViewResults(webapp2.RequestHandler):
    def get(self):
        """Show results by gathering stats from db"""

        template_values = get_progress_stats('info_to_breakdown')

        template = jinja_environment.get_template('pie_chart.html')
        self.response.out.write(template.render(template_values))
