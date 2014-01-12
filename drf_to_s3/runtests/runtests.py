#!/usr/bin/env python
'''
From django-rest-framework
https://github.com/tomchristie/django-rest-framework/blob/master/rest_framework/runtests/runtests.py
'''

# http://ericholscher.com/blog/2009/jun/29/enable-setuppy-test-your-django-apps/
# http://www.travisswicegood.com/2010/01/17/django-virtualenv-pip-and-fabric/
# http://code.djangoproject.com/svn/django/trunk/tests/runtests.py
import os
import sys

# fix sys path so we don't need to setup PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
os.environ['DJANGO_SETTINGS_MODULE'] = 'drf_to_s3.runtests.settings'

import django
from django.conf import settings
from django.test.utils import get_runner


def usage():
    return """
    Usage: runtests.py module.submodule.class.method

    You can pass the module and class name you want to test.

    Append a method name if you only want to test a specific method of that class.

    With no arguments, it runs the unit tests, in tests/.

    To run the integration tests, use runtests.py integration.
    """


def main():
    TestRunner = get_runner(settings)

    test_runner = TestRunner()
    if len(sys.argv) == 2:
        test_case = sys.argv[1]
    elif len(sys.argv) == 1:
        test_case = 'tests'
    else:
        print(usage())
        sys.exit(1)
    test_module_name = 'drf_to_s3.'
    if django.VERSION[0] == 1 and django.VERSION[1] < 6:
        test_module_name = ''

    failures = test_runner.run_tests([test_module_name + test_case])

    sys.exit(failures)

if __name__ == '__main__':
    main()
