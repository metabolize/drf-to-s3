from django.test import TestCase
from rest_framework.parsers import JSONParser
from s3_upload.serializers import UploadPolicyConditionField

class UploadPolicyConditionFieldTest(TestCase):

    def setUp(self):
        self.parser = JSONParser()  
        self.field = UploadPolicyConditionField()      

    def test_starts_with(self):
        json_data = '["starts-with", "$key", "user/eric/"]'
        data = self.parser.parse(json_data)
        result = self.field.from_native(data)
        self.assertEquals(result.operator, 'starts-with')
        self.assertEquals(result.key, 'key'),
        self.assertEquals(result.value, 'user/eric/')
        self.assertIsNone(result.value_range)
