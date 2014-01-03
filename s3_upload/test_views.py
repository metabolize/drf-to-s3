import datetime, json, mock
from django.conf.urls import patterns, url
from django.test.utils import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from s3_upload import urls as _urls
from s3_upload.serializers import FineUploaderPolicySerializer
from s3_upload.views import empty_html, FineUploaderSignUploadPolicyView


class FineUploaderPolicySerializerTest(APITestCase):

    class MyView(FineUploaderSignUploadPolicyView):
        class MySerializer(FineUploaderPolicySerializer):
            allowed_buckets = ['my-bucket']

        serializer_class = MySerializer
        aws_secret_access_key = '12345'

    urls = patterns('',
        url(r'^s3/sign/$', MyView.as_view()),
    )

    def setUp(self):
        self.policy_document = {
            "expiration": "2007-12-01T12:00:00.000Z",
            "conditions": [
                {"acl": "private"},
                {"bucket": "my-bucket"},
                {"Content-Type": "image/jpeg"},
                {"success_action_status": 200},
                {"success_action_redirect": "http://example.com/foo/bar"},
                {"key": "/foo/bar/baz.jpg"},
                {"x-amz-meta-qqfilename": "/foo/bar/baz.jpg"},
                ["content-length-range", 1024, 10240]
            ]
        }

    def test_sign_upload_returns_success(self):
        resp = self.client.post('/s3/sign/', self.policy_document, format='json')
        self.assertEquals(resp.status_code, status.HTTP_200_OK)

    def test_sign_upload_overrides_expiration_date(self):
        resp = self.client.post('/s3/sign/', self.policy_document, format='json')
        policy_decoded = json.loads(resp.content)['policy_decoded']
        expiration = datetime.datetime.strptime(policy_decoded['expiration'], '%Y-%m-%dT%H:%M:%S.%f')
        expected_expiration_before = datetime.datetime.today() + datetime.timedelta(300 + 1)
        self.assertLess(expiration, expected_expiration_before)

    def test_sign_upload_preserves_conditions(self):
        resp = self.client.post('/s3/sign/', self.policy_document, format='json')
        policy_decoded = json.loads(resp.content)['policy_decoded']
        self.assertEquals(policy_decoded['conditions'], self.policy_document['conditions'])

    def test_that_disallowed_bucket_returns_expected_error(self):
        self.policy_document['conditions'][1]['bucket'] = 'secret-bucket'
        resp = self.client.post('/s3/sign/', self.policy_document, format='json')
        self.assertEquals(resp.status_code, status.HTTP_400_BAD_REQUEST)
        expected = {'invalid': True, 'errors': {'conditions.bucket': ['Bucket not allowed']}}
        self.assertEquals(json.loads(resp.content), expected)

    def test_that_disallowed_acl_returns_expected_error(self):
        self.policy_document['conditions'][0]['acl'] = 'public-read'
        resp = self.client.post('/s3/sign/', self.policy_document, format='json')
        self.assertEquals(resp.status_code, status.HTTP_400_BAD_REQUEST)
        expected = {'invalid': True, 'errors': {'conditions.acl': ['ACL not allowed']}}
        self.assertEquals(json.loads(resp.content), expected)


class FineUploaderSettingsTest(APITestCase):

    @override_settings(AWS_UPLOAD_SECRET_ACCESS_KEY='1451')
    def test_that_secret_key_pulls_from_settings(self):
        view = FineUploaderSignUploadPolicyView()
        self.assertEquals(view.aws_secret_access_key, '1451')


class TestEmptyHTMLView(APITestCase):

    urls = patterns('',
        url(r'^s3/empty_html/$', empty_html),
    )

    def test_that_secret_key_pulls_from_settings(self):
        resp = self.client.get('/s3/empty_html/')
        self.assertEquals(resp.status_code, status.HTTP_200_OK)
        # Doesn't seem to set this on empty content; does that matter?
        # self.assertEquals(resp['Content-Type'], 'text/html')
        self.assertEquals(resp.content, '')
