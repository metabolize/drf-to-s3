import datetime, json, mock, unittest
from django.core.exceptions import ValidationError
from drf_to_s3.models import Policy, PolicyCondition
from drf_to_s3.serializers import FinePolicySerializer


class FineUploaderPolicySerializerTest(unittest.TestCase):

    class MySerializer(FinePolicySerializer):
        allowed_buckets = ['my-bucket']

    def setUp(self):
        self.serializer_class = self.MySerializer

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
        serializer.allowed_buckets = ['my-bucket']
        serializer.allowed_acls = ['public-read']
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
        serializer.allowed_buckets = ['my-bucket']
        serializer.allowed_acls = ['public-read']
        expected = ['Required condition is missing']
        self.assertEquals(serializer.errors['conditions.key'], expected)

    def test_that_serialize_with_reversed_content_length_fails(self):
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
                ["content-length-range", 10240, 1024]
            ]
        }
        '''
        data = json.loads(json_data)
        serializer = self.serializer_class(data=data)
        serializer.allowed_buckets = ['my-bucket']
        serializer.allowed_acls = ['public-read']
        expected = ['content_length_range should be ordered ascending']
        self.assertEquals(serializer.errors['conditions.content-length-range'], expected)

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
        serializer.allowed_buckets = ['my-bucket']
        serializer.allowed_acls = ['public-read']
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
        serializer.allowed_buckets = ['my-bucket']
        serializer.allowed_acls = ['public-read']
        expected = ['Invalid character in key']
        self.assertEquals(serializer.errors['conditions.key'], expected)
