import datetime, json, mock, unittest
from django.core.exceptions import ValidationError
from rest_framework.parsers import JSONParser
from s3_upload.models import UploadPolicy, UploadPolicyCondition
from s3_upload.serializers import UploadPolicyConditionField, BaseUploadPolicySerializer, FineUploaderPolicySerializer, MyFineUploaderPolicySerializer


class UploadPolicyConditionFieldTest(unittest.TestCase):

    def setUp(self):
        self.field = UploadPolicyConditionField()      

    def test_starts_with(self):
        json_data = '["starts-with", "$key", "user/eric/"]'
        result = self.field.from_native(json.loads(json_data))
        self.assertIsInstance(result, UploadPolicyCondition)
        self.assertEquals(result.operator, 'starts-with')
        self.assertEquals(result.element_name, 'key'),
        self.assertEquals(result.value, 'user/eric/')
        self.assertIsNone(result.value_range)

    def test_eq(self):
        json_data = '[ "eq", "$acl", "public-read" ]'
        result = self.field.from_native(json.loads(json_data))
        self.assertIsInstance(result, UploadPolicyCondition)
        self.assertEquals(result.operator, 'eq')
        self.assertEquals(result.element_name, 'acl'),
        self.assertEquals(result.value, 'public-read')
        self.assertIsNone(result.value_range)

    def test_range(self):
        json_data = '["content-length-range", 1048579, 10485760]'
        result = self.field.from_native(json.loads(json_data))
        self.assertIsInstance(result, UploadPolicyCondition)
        self.assertIsNone(result.operator)
        self.assertEquals(result.element_name, 'content-length-range'),
        self.assertIsNone(result.value)
        self.assertEquals(result.value_range, [1048579, 10485760])

    def test_empty_array(self):
        data = []
        with self.assertRaises(ValidationError) as ctx:
            self.field.from_native(data)
        exception = ctx.exception
        self.assertTrue(exception.message.startswith('Empty condition array'))
        self.assertEquals(exception.params['condition'], data)

    def test_missing_args(self):
        json_data = '["content-length-range"]'
        data = json.loads(json_data)
        with self.assertRaises(ValidationError) as ctx:
            self.field.from_native(data)
        exception = ctx.exception
        self.assertTrue(exception.message.startswith('Missing values in condition array'))
        self.assertEquals(exception.params['condition'], data)

    def test_missing_key(self):
        json_data = '["eq"]'
        data = json.loads(json_data)
        with self.assertRaises(ValidationError) as ctx:
            self.field.from_native(data)
        exception = ctx.exception
        self.assertTrue(exception.message.startswith('Missing element in condition array'))
        self.assertEquals(exception.params['condition'], data)

    def test_missing_dollar(self):
        json_data = '["eq", "key"]'
        data = json.loads(json_data)
        with self.assertRaises(ValidationError) as ctx:
            self.field.from_native(data)
        exception = ctx.exception
        self.assertTrue(exception.message.startswith('Element name in condition array should start with $'))
        self.assertEquals(exception.params['element_name'], 'key')

    def test_extra_args(self):
        json_data = '["content-length-range", 1, 2, 3, 4, 5]'
        data = json.loads(json_data)
        with self.assertRaises(ValidationError) as ctx:
            self.field.from_native(data)
        exception = ctx.exception
        self.assertTrue(exception.message.startswith('Too many values in condition array'))
        self.assertEquals(exception.params['condition'], data)

    def test_dict(self):
        json_data = '{"acl": "public-read" }'
        result = self.field.from_native(json.loads(json_data))
        self.assertIsInstance(result, UploadPolicyCondition)
        self.assertIsNone(result.operator)
        self.assertEquals(result.element_name, 'acl')
        self.assertEquals(result.value, 'public-read')
        self.assertIsNone(result.value_range)

    def test_dict_extra_keys(self):
        json_data = '{"acl": "public-read", "foo": "bar"}'
        data = json.loads(json_data)
        with self.assertRaises(ValidationError) as ctx:
            self.field.from_native(data)
        exception = ctx.exception
        self.assertTrue(exception.message.startswith('Too many values in condition dictionary'))
        self.assertEquals(exception.params['condition'], data)

    def test_dict_invalid_values(self):
        json_data = '{"acl": []}'
        data = json.loads(json_data)
        with self.assertRaises(ValidationError) as ctx:
            self.field.from_native(data)
        exception = ctx.exception
        self.assertEquals(exception.message, 'Values in condition dictionaries should be numbers or strings')

    def test_string(self):
        data = 'foo-test'
        with self.assertRaises(ValidationError) as ctx:
            self.field.from_native(data)
        exception = ctx.exception
        self.assertTrue(exception.message.startswith('Condition must be array or dictionary'))
        self.assertEquals(exception.params['condition'], data)

    def test_number(self):
        data = 12345
        with self.assertRaises(ValidationError) as ctx:
            self.field.from_native(data)
        exception = ctx.exception
        self.assertTrue(exception.message.startswith('Condition must be array or dictionary'))
        self.assertEquals(exception.params['condition'], data)


class BaseUploadPolicySerializerTest(unittest.TestCase):

    def test_that_serialize_with_bucket_succeeds(self):
        json_data = '''
        {
            "expiration": "2007-12-01T12:00:00.000Z",
            "conditions": [
                {"bucket": "johnsmith" }
            ]
        }
        '''
        data = json.loads(json_data)
        serializer = BaseUploadPolicySerializer(data=data)
        serializer.allowed_buckets = ['johnsmith']
        self.assertTrue(serializer.is_valid())

    def test_that_serialize_without_bucket_fails(self):
        json_data = '''
        {
            "expiration": "2007-12-01T12:00:00.000Z",
            "conditions": [
            ]
        }
        '''
        data = json.loads(json_data)
        serializer = BaseUploadPolicySerializer(data=data)
        self.assertFalse(serializer.is_valid())
        expected = ['Required condition is missing']
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
        serializer = BaseUploadPolicySerializer(data=data)
        self.assertFalse(serializer.is_valid())
        expected = ['Invalid element name: foo']
        self.assertEquals(serializer.errors['conditions'], expected)

    def test_that_after_configuration_serialize_without_bucket_succeeds(self):
        json_data = '''
        {
            "expiration": "2007-12-01T12:00:00.000Z",
            "conditions": [
            ]
        }
        '''
        data = json.loads(json_data)
        serializer = BaseUploadPolicySerializer(data=data)
        serializer.required_conditions = []
        self.assertTrue(serializer.is_valid())

    def test_that_after_configuration_serialize_with_extra_condition_succeeds(self):
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
        serializer = BaseUploadPolicySerializer(data=data)
        serializer.allowed_buckets = ['johnsmith']
        serializer.optional_conditions = ['foo']
        self.assertTrue(serializer.is_valid())

    @unittest.expectedFailure # Need to figure out why
    def test_that_serializer_invokes_validate_expiration(self):
        json_data = '''
        {
            "expiration": "2007-12-01T12:00:00.000Z",
            "conditions": [
                {"bucket": "johnsmith" }
            ]
        }
        '''
        data = json.loads(json_data)
        serializer = BaseUploadPolicySerializer(data=data)
        serializer.validate_expiration = mock.MagicMock()
        self.assertTrue(serializer.validate_expiration.called)

    @unittest.expectedFailure # Need to figure out why
    def test_that_serializer_invokes_validate_condition_methods(self):
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
        serializer = BaseUploadPolicySerializer(data=data)
        serializer.optional_conditions = ['foo']
        serializer.validate_condition_bucket = mock.MagicMock()
        serializer.validate_condition_foo = mock.MagicMock()
        self.assertTrue(serializer.validate_condition_bucket.called)
        self.assertTrue(serializer.validate_condition_foo.called)

    # FIXME Test that errors generated by condition validation methods
    # are returned

    # FIXME Test that when there's a missing key and a condition validation
    # error, both are returned

    def test_that_after_configuration_serialize_with_valid_bucket_succeeds(self):
        json_data = '''
        {
            "expiration": "2007-12-01T12:00:00.000Z",
            "conditions": [
                {"bucket": "johnsmith"}
            ]
        }
        '''
        data = json.loads(json_data)
        serializer = BaseUploadPolicySerializer(data=data)
        serializer.allowed_buckets = ['janesmith', 'johnsmith']
        self.assertTrue(serializer.is_valid())

    def test_that_after_configuration_serialize_with_invalid_bucket_fails(self):
        json_data = '''
        {
            "expiration": "2007-12-01T12:00:00.000Z",
            "conditions": [
                {"bucket": "joesmith"}
            ]
        }
        '''
        data = json.loads(json_data)
        serializer = BaseUploadPolicySerializer(data=data)
        serializer.allowed_buckets = ['janesmith', 'johnsmith']
        self.assertFalse(serializer.is_valid())
        expected = ['Bucket not allowed']
        self.assertEquals(serializer.errors['conditions.bucket'], expected)

    def test_that_after_configuration_serialize_with_valid_content_type_succeeds(self):
        json_data = '''
        {
            "expiration": "2007-12-01T12:00:00.000Z",
            "conditions": [
                {"Content-Type": "image/jpeg"}
            ]
        }
        '''
        data = json.loads(json_data)
        serializer = BaseUploadPolicySerializer(data=data)
        serializer.required_conditions = []
        self.assertTrue(serializer.is_valid())

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
        serializer = BaseUploadPolicySerializer(data=data)
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
        serializer = BaseUploadPolicySerializer(data=data)
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
        serializer = BaseUploadPolicySerializer(data=data)
        serializer.required_conditions = []
        expected = ['Invalid Content-Type']
        self.assertEquals(serializer.errors['conditions.Content-Type'], expected)

    def test_that_after_configuration_serialize_with_invalid_success_action_status_fails(self):
        json_data = '''
        {
            "expiration": "2007-12-01T12:00:00.000Z",
            "conditions": [
                {"success_action_status": "100"}
            ]
        }
        '''
        data = json.loads(json_data)
        serializer = BaseUploadPolicySerializer(data=data)
        serializer.required_conditions = []
        serializer.optional_conditions = ['success_action_status']
        expected = ['success_action_status should be between 200 and 399']
        self.assertEquals(serializer.errors['conditions.success_action_status'], expected)

        json_data = '''
        {
            "expiration": "2007-12-01T12:00:00.000Z",
            "conditions": [
                {"success_action_status": 400}
            ]
        }
        '''
        data = json.loads(json_data)
        serializer = BaseUploadPolicySerializer(data=data)
        serializer.required_conditions = []
        serializer.optional_conditions = ['success_action_status']
        expected = ['success_action_status should be between 200 and 399']
        self.assertEquals(serializer.errors['conditions.success_action_status'], expected)

        json_data = '''
        {
            "expiration": "2007-12-01T12:00:00.000Z",
            "conditions": [
                {"success_action_status": "1.2"}
            ]
        }
        '''
        data = json.loads(json_data)
        serializer = BaseUploadPolicySerializer(data=data)
        serializer.required_conditions = []
        serializer.optional_conditions = ['success_action_status']
        expected = ['Invalid success_action_status']
        self.assertEquals(serializer.errors['conditions.success_action_status'], expected)

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
        serializer = BaseUploadPolicySerializer(data=data)
        serializer.required_conditions = []
        serializer.optional_conditions = ['key']
        expected = ['Invalid key']
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
        serializer = BaseUploadPolicySerializer(data=data)
        serializer.required_conditions = []
        serializer.optional_conditions = ['x-amz-meta-qqfilename']
        expected = ['Invalid character in x-amz-meta-qqfilename']
        self.assertEquals(serializer.errors['conditions.x-amz-meta-qqfilename'], expected)

class FineUploaderPolicySerializerTest(unittest.TestCase):

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
        serializer = FineUploaderPolicySerializer(data=data)
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
        serializer = FineUploaderPolicySerializer(data=data)
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
        serializer = FineUploaderPolicySerializer(data=data)
        serializer.allowed_buckets = ['my-bucket']
        serializer.allowed_acls = ['public-read']
        expected = ['content_length_range should be ordered ascending']
        self.assertEquals(serializer.errors['conditions.content-length-range'], expected)

class MyFineUploaderPolicySerializerTest(unittest.TestCase):

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
        serializer = MyFineUploaderPolicySerializer(data=data)
        serializer.allowed_buckets = ['my-bucket']
        serializer.allowed_acls = ['public-read']
        self.assertTrue(serializer.is_valid())
        result = serializer.object
        self.assertIsInstance(result['expiration'], datetime.datetime)
        self.assertEquals(len(result['conditions']), 8)

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
        serializer = MyFineUploaderPolicySerializer(data=data)
        serializer.allowed_buckets = ['my-bucket']
        serializer.allowed_acls = ['public-read']
        expected = ['Invalid character in key']
        self.assertEquals(serializer.errors['conditions.key'], expected)
