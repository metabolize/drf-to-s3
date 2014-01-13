import unittest, urllib
from rest_framework.compat import BytesIO


class TestParser(unittest.TestCase):

    def setUp(self):
        from drf_to_s3.parsers import NestedFormParser
        self.parser = NestedFormParser()

    def test_form_parser_unflattens(self):
        flattened = {
            'user[name]': 'Foobar',
            'user[email]': 'foo@bar.com',
        }

        stream = BytesIO(urllib.urlencode(flattened))
        result = self.parser.parse(stream, 'application/x-www-form-urlencoded', {})

        expected = {
            'user': {
                'name': 'Foobar',
                'email': 'foo@bar.com',
            }
        }
        self.assertEquals(result, expected)
