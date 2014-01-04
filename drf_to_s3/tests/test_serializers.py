import datetime, json, unittest
from django.core.exceptions import ValidationError


class DefaultPolicySerializerTest(unittest.TestCase):

    def setUp(self):
        from drf_to_s3.serializers import DefaultPolicySerializer
        self.serializer_class = DefaultPolicySerializer

    def test_serialize_is_valid(self):
        json_data = '''
        {
            "expiration": "2007-12-01T12:00:00.000Z",
            "conditions": [
                {"acl": "public-read"},
                {"bucket": "my-bucket"},
                {"Content-Type": "image/jpeg"},
                {"success_action_status": 200},
                {"success_action_redirect": "http://example.com/foo/bar"},
                {"key": "/foo/bar/baz.jpg"},
                {"x-amz-meta-qqfilename": "/foo/bar/baz.jpg"},
                ["content-length-range", 1024, 10240]
            ]
        }
        '''
        data = json.loads(json_data)
        serializer = self.serializer_class(data=data)
        self.assertTrue(serializer.is_valid())
        result = serializer.object
        self.assertIsInstance(result['expiration'], datetime.datetime)
        self.assertEquals(len(result['conditions']), 8)

    def test_that_serialize_with_missing_key_fails(self):
        json_data = '''
        {
            "expiration": "2007-12-01T12:00:00.000Z",
            "conditions": [
                {"acl": "public-read"},
                {"bucket": "my-bucket"},
                {"Content-Type": "image/jpeg"},
                {"success_action_status": 200},
                {"success_action_redirect": "http://example.com/foo/bar"},
                {"x-amz-meta-qqfilename": "/foo/bar/baz.jpg"},
                ["content-length-range", 1024, 10240]
            ]
        }
        '''
        data = json.loads(json_data)
        serializer = self.serializer_class(data=data)
        expected = ['Required condition is missing']
        self.assertEquals(serializer.errors['conditions.key'], expected)

    def test_serialize_is_valid(self):
        json_data = '''
        {
            "expiration": "2007-12-01T12:00:00.000Z",
            "conditions": [
                {"acl": "public-read"},
                {"bucket": "my-bucket"},
                {"Content-Type": "image/jpeg"},
                {"success_action_status": 200},
                {"success_action_redirect": "http://example.com/foo/bar"},
                {"key": "/foo/bar/baz.jpg"},
                {"x-amz-meta-qqfilename": "/foo/bar/baz.jpg"},
                ["content-length-range", 1024, 10240]
            ]
        }
        '''
        data = json.loads(json_data)
        serializer = self.serializer_class(data=data)
        self.assertTrue(serializer.is_valid())
        result = serializer.object
        self.assertIsInstance(result.expiration, datetime.datetime)
        self.assertEquals(len(result.conditions), 8)

    def test_that_serialize_with_invalid_key_fails(self):
        json_data = '''
        {
            "expiration": "2007-12-01T12:00:00.000Z",
            "conditions": [
                {"acl": "public-read"},
                {"bucket": "my-bucket"},
                {"Content-Type": "image/jpeg"},
                {"success_action_status": 200},
                {"success_action_redirect": "http://example.com/foo/bar"},
                {"key": "/foo/bar\\baz.jpg"},
                {"x-amz-meta-qqfilename": "/foo/bar/baz.jpg"},
                ["content-length-range", 1024, 10240]
            ]
        }
        '''
        data = json.loads(json_data)
        serializer = self.serializer_class(data=data)
        expected = ['Invalid character in key']
        self.assertEquals(serializer.errors['conditions.key'], expected)

    def test_that_after_configuration_serialize_with_invalid_content_type_fails(self):
        json_data = '''
        {
            "expiration": "2007-12-01T12:00:00.000Z",
            "conditions": [
                {"Content-Type": ""}
            ]
        }
        '''
        data = json.loads(json_data)
        serializer = self.serializer_class(data=data)
        serializer.required_conditions = []
        expected = ['Invalid Content-Type']
        self.assertEquals(serializer.errors['conditions.Content-Type'], expected)

        json_data = '''
        {
            "expiration": "2007-12-01T12:00:00.000Z",
            "conditions": [
                {"Content-Type": "foo/bar/baz"}
            ]
        }
        '''
        data = json.loads(json_data)
        serializer = self.serializer_class(data=data)
        serializer.required_conditions = []
        expected = ['Invalid Content-Type']
        self.assertEquals(serializer.errors['conditions.Content-Type'], expected)

        json_data = '''
        {
            "expiration": "2007-12-01T12:00:00.000Z",
            "conditions": [
                {"Content-Type": "foo/bar@baz"}
            ]
        }
        '''
        data = json.loads(json_data)
        serializer = self.serializer_class(data=data)
        serializer.required_conditions = []
        expected = ['Invalid Content-Type']
        self.assertEquals(serializer.errors['conditions.Content-Type'], expected)

    def test_that_serialize_with_invalid_key_fails(self):
        json_data = '''
        {
            "expiration": "2007-12-01T12:00:00.000Z",
            "conditions": [
                {"key": 123}
            ]
        }
        '''
        data = json.loads(json_data)
        serializer = self.serializer_class(data=data)
        serializer.required_conditions = []
        serializer.optional_conditions = ['key']
        expected = ['Key should be a string']
        self.assertEquals(serializer.errors['conditions.key'], expected)

    def test_that_serialize_with_invalid_filename_fails(self):
        json_data = '''
        {
            "expiration": "2007-12-01T12:00:00.000Z",
            "conditions": [
                {"x-amz-meta-qqfilename": "foo/bar\\baz.jpg"}
            ]
        }
        '''
        data = json.loads(json_data)
        serializer = self.serializer_class(data=data)
        serializer.required_conditions = []
        serializer.optional_conditions = ['x-amz-meta-qqfilename']
        expected = ['Invalid character in x-amz-meta-qqfilename']
        self.assertEquals(serializer.errors['conditions.x-amz-meta-qqfilename'], expected)

    def test_that_serialize_with_invalid_bucket_fails(self):
        json_data = '''
        {
            "expiration": "2007-12-01T12:00:00.000Z",
            "conditions": [
                {"bucket": "bad bucket"}
            ]
        }
        '''
        data = json.loads(json_data)
        serializer = self.serializer_class(data=data)
        self.assertFalse(serializer.is_valid())
        expected = ['Invalid bucket name']
        self.assertEquals(serializer.errors['conditions.bucket'], expected)

    def test_that_serialize_with_extra_condition_fails(self):
        json_data = '''
        {
            "expiration": "2007-12-01T12:00:00.000Z",
            "conditions": [
                {"bucket": "johnsmith" },
                {"foo": "bar" }
            ]
        }
        '''
        data = json.loads(json_data)
        serializer = self.serializer_class(data=data)
        self.assertFalse(serializer.is_valid())
        expected = ['Invalid element name']
        self.assertEquals(serializer.errors['conditions.foo'], expected)

    def test_that_serialize_without_bucket_fails(self):
        json_data = '''
        {
            "expiration": "2007-12-01T12:00:00.000Z",
            "conditions": [
            ]
        }
        '''
        data = json.loads(json_data)
        serializer = self.serializer_class(data=data)
        self.assertFalse(serializer.is_valid())
        expected = ['Required condition is missing']
        self.assertEquals(serializer.errors['conditions.bucket'], expected)
