from rest_framework import parsers


class NestedFormParser(parsers.BaseParser):
    '''
    Parses form data with nested elements, such as if you
    pass a dictionary parameter in Fine Uploader as a
    parameter to the upload success callback.

    Uses https://github.com/aventurella/pyquerystring

    e.g. Will transform:

        {
            'user[name]': 'Foobar',
            'user[email]': 'foo@bar.com',
        }

    to:

        {
            'user': {
                'name': 'Foobar',
                'email': 'foo@bar.com',
            }
        }

    By default Django REST Framework will automatically parse
    form data before the parsers get involved. To use this
    parser you need to disable that behavior.

        REST_FRAMEWORK = {
            'FORM_METHOD_OVERRIDE': None,
            'FORM_CONTENT_OVERRIDE': None,
        }

    Note this only works for application/x-www-form-urlencoded,
    and not multipart/form-data which the Django test client
    generates. To use this with the Django test client, you can
    flatten and encode the content and set the header yourself:

        import urllib
        data = {
            'foo': 'bar',
            'bar[stuff]': 'here',
        }
        resp = self.client.post(
            '/api',
            urllib.urlencode(data),
            content_type='application/x-www-form-urlencoded'
        )
    
    '''
    media_type = 'application/x-www-form-urlencoded'

    def parse(self, stream, media_type=None, parser_context=None):
        from querystring_parser import parser
        from django.conf import settings

        encoding = parser_context.get('encoding', settings.DEFAULT_CHARSET)
        encoded_data = stream.read().decode(encoding)
        return parser.parse(encoded_data)
