import coverage
import unittest

if __name__ == "__main__":
    cov = coverage.Coverage()

    cov.start()
    suite = unittest.TestLoader().discover("streamanalyser/tests", pattern="*")
    unittest.TextTestRunner().run(suite)
    cov.stop()

    cov.save()

    cov.report()

    cov.html_report()
