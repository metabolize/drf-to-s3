import datetime, json, mock, unittest
from django.conf.urls import patterns, url
from django.test.utils import override_settings
from rest_framework import status
from rest_framework.test import APITestCase


@override_settings(
    AWS_UPLOAD_SECRET_ACCESS_KEY='12345',
    AWS_UPLOAD_BUCKET='my-bucket',
    AWS_UPLOAD_PREFIX_FUNC=lambda x: 'uploads'
)
class FineSignPolicyViewTestWithoutAuth(APITestCase):
    urls = 'drf_to_s3.urls'

    def setUp(self):
        self.policy_document = {
            "expiration": "2007-12-01T12:00:00.000Z",
            "conditions": [
                {"acl": "private"},
                {"bucket": "my-bucket"},
                {"Content-Type": "image/jpeg"},
                {"success_action_status": 200},
                {"success_action_redirect": "http://example.com/foo/bar"},
                {"key": "uploads/foo/bar/baz.jpg"},
                {"x-amz-meta-qqfilename": "baz.jpg"},
                ["content-length-range", 1024, 10240]
            ]
        }

    def test_sign_upload_returns_success(self):
        resp = self.client.post('/sign', self.policy_document, format='json')
        self.assertEquals(resp.status_code, status.HTTP_200_OK)
        content = json.loads(resp.content)
        with self.assertRaises(KeyError):
            content['invalid']

    def test_sign_upload_overrides_expiration_date(self):
        resp = self.client.post('/sign', self.policy_document, format='json')
        policy_decoded = json.loads(resp.content)['policy_decoded']
        expiration = datetime.datetime.strptime(policy_decoded['expiration'], '%Y-%m-%dT%H:%M:%SZ')
        expected_expiration_before = datetime.datetime.today() + datetime.timedelta(300 + 1)
        self.assertLess(expiration, expected_expiration_before)

    def test_sign_upload_preserves_conditions(self):
        resp = self.client.post('/sign', self.policy_document, format='json')
        policy_decoded = json.loads(resp.content)['policy_decoded']
        self.assertEquals(policy_decoded['conditions'], self.policy_document['conditions'])

    def test_that_disallowed_bucket_returns_expected_error(self):
        self.policy_document['conditions'][1]['bucket'] = 'secret-bucket'
        resp = self.client.post('/sign', self.policy_document, format='json')
        self.assertEquals(resp.status_code, status.HTTP_403_FORBIDDEN)
        expected = {'invalid': True, 'error': "Bucket should be 'my-bucket'"}
        self.assertEquals(json.loads(resp.content), expected)

    def test_that_disallowed_acl_returns_expected_error(self):
        self.policy_document['conditions'][0]['acl'] = 'public-read'
        resp = self.client.post('/sign', self.policy_document, format='json')
        self.assertEquals(resp.status_code, status.HTTP_403_FORBIDDEN)
        expected = {'invalid': True, 'error': "ACL should be 'private'"}
        self.assertEquals(json.loads(resp.content), expected)


@override_settings(
    AWS_UPLOAD_SECRET_ACCESS_KEY='12345',
    AWS_UPLOAD_BUCKET='my-bucket'
)
class FineSignPolicyViewSessionAuthTest(APITestCase):
    urls = 'drf_to_s3.urls'

    def setUp(self):
        from .util import get_user_model
        self.username = 'frodo'
        self.password = 'shire1234'
        user = get_user_model().objects.create_user(
            username=self.username,
            password=self.password
        )

    def test_that_sign_upload_accepts_username_as_prefix(self):
        self.client.login(
            username=self.username,
            password=self.password
        )
        prefix = self.username
        self.policy_document = {
            "expiration": "2007-12-01T12:00:00.000Z",
            "conditions": [
                {"acl": "private"},
                {"bucket": "my-bucket"},
                {"Content-Type": "image/jpeg"},
                {"success_action_status": 200},
                {"success_action_redirect": "http://example.com/foo/bar"},
                {"key": prefix + "/foo/bar/baz.jpg"},
                {"x-amz-meta-qqfilename": "baz.jpg"},
                ["content-length-range", 1024, 10240]
            ]
        }
        resp = self.client.post('/sign', self.policy_document, format='json')
        self.assertEquals(resp.status_code, status.HTTP_200_OK)
        content = json.loads(resp.content)
        with self.assertRaises(KeyError):
            content['invalid']

    def test_that_sign_upload_without_prefix_fails(self):
        self.client.login(
            username=self.username,
            password=self.password
        )
        prefix = ''
        self.policy_document = {
            "expiration": "2007-12-01T12:00:00.000Z",
            "conditions": [
                {"acl": "private"},
                {"bucket": "my-bucket"},
                {"Content-Type": "image/jpeg"},
                {"success_action_status": 200},
                {"success_action_redirect": "http://example.com/foo/bar"},
                {"key": prefix + "/foo/bar/baz.jpg"},
                {"x-amz-meta-qqfilename": "baz.jpg"},
                ["content-length-range", 1024, 10240]
            ]
        }
        resp = self.client.post('/sign', self.policy_document, format='json')
        self.assertEquals(resp.status_code, status.HTTP_403_FORBIDDEN)
        content = json.loads(resp.content)
        self.assertTrue(content['invalid'])
        self.assertTrue(content['error'].startswith('Key should start with '))

    def test_that_sign_upload_with_unauthenticated_user_fails(self):
        # FIXME This needs to return a proper error response
        prefix = self.username
        self.policy_document = {
            "expiration": "2007-12-01T12:00:00.000Z",
            "conditions": [
                {"acl": "private"},
                {"bucket": "my-bucket"},
                {"Content-Type": "image/jpeg"},
                {"success_action_status": 200},
                {"success_action_redirect": "http://example.com/foo/bar"},
                {"key": prefix + "/foo/bar/baz.jpg"},
                {"x-amz-meta-qqfilename": "baz.jpg"},
                ["content-length-range", 1024, 10240]
            ]
        }
        resp = self.client.post('/sign', self.policy_document, format='json')
        self.assertEquals(resp.status_code, status.HTTP_403_FORBIDDEN)
        content = json.loads(resp.content)
        self.assertTrue(content['invalid'])
        self.assertTrue(content['error'].startswith('Log in before uploading'))


class FineUploaderSettingsTest(APITestCase):

    @override_settings(AWS_UPLOAD_SECRET_ACCESS_KEY='1451')
    def test_that_secret_key_pulls_from_settings(self):
        from drf_to_s3.views import FineSignPolicyView
        view = FineSignPolicyView()
        self.assertEquals(view.get_aws_secret_access_key(), '1451')
