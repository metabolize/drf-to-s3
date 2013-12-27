import json, unittest
from django.core.exceptions import ValidationError
from rest_framework.parsers import JSONParser
from s3_upload.serializers import UploadPolicyConditionField


class UploadPolicyConditionFieldTest(unittest.TestCase):

    def setUp(self):
        self.field = UploadPolicyConditionField()      

    def test_starts_with(self):
        json_data = '["starts-with", "$key", "user/eric/"]'
        result = self.field.from_native(json.loads(json_data))
        self.assertEquals(result.operator, 'starts-with')
        self.assertEquals(result.key, 'key'),
        self.assertEquals(result.value, 'user/eric/')
        self.assertIsNone(result.value_range)

    def test_eq(self):
        json_data = '[ "eq", "$acl", "public-read" ]'
        result = self.field.from_native(json.loads(json_data))
        self.assertEquals(result.operator, 'eq')
        self.assertEquals(result.key, 'acl'),
        self.assertEquals(result.value, 'public-read')
        self.assertIsNone(result.value_range)

    def test_range(self):
        json_data = '["content-length-range", 1048579, 10485760]'
        result = self.field.from_native(json.loads(json_data))
        self.assertIsNone(result.operator)
        self.assertEquals(result.key, 'content-length-range'),
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
        self.assertTrue(exception.message.startswith('Missing key in condition array'))
        self.assertEquals(exception.params['condition'], data)

    def test_missing_dollar(self):
        json_data = '["eq", "key"]'
        data = json.loads(json_data)
        with self.assertRaises(ValidationError) as ctx:
            self.field.from_native(data)
        exception = ctx.exception
        self.assertTrue(exception.message.startswith('Key in condition array should start with $'))
        self.assertEquals(exception.params['key'], 'key')

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
        self.assertIsNone(result.operator)
        self.assertEquals(result.key, 'acl')
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
