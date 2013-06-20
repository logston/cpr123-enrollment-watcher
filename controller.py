import webapp2

app = webapp2.WSGIApplication(
    [
    ('/CollectAllClasses', 'collection_routines.CollectAllClasses'),
    ('/CollectPastClasses', 'collection_routines.CollectPastClasses'),
    ('/CollectUpcomingClasses', 'collection_routines.CollectUpcomingClasses'),
    ('/CollectPastEnrollments', 'collection_routines.CollectPastEnrollments'),
    ('/CollectEnrollments', 'collection_routines.CollectEnrollments'),
    ('/CollectZipCodes', 'collection_routines.CollectZipCodes'),
    ('/CollectGrades', 'collection_routines.CollectGrades'),
    ('/CollectAllCurrentGrades', 'collection_routines.CollectAllCurrentGrades'),
    ('/ViewProgress', 'views.ViewProgress'),
    ('/ViewResults', 'views.ViewResults')
    ], debug=True)
