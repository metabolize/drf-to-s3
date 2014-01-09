import datetime, json, mock, unittest
from django.conf.urls import patterns, url
from django.test.utils import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from .util import establish_session


class FineSignPolicyViewTest(APITestCase):
    from drf_to_s3.views import FineSignPolicyView
    urls = patterns('',
        url(r'^s3/sign/$', FineSignPolicyView.as_view()),
    )
    override_settings = {
        'AWS_UPLOAD_SECRET_ACCESS_KEY': '12345',
        'AWS_UPLOAD_BUCKET': 'my-bucket',
        'AWS_UPLOAD_PREFIX_FUNC': lambda x: 'uploads',
    }

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
        resp = self.client.post('/s3/sign/', self.policy_document, format='json')
        self.assertEquals(resp.status_code, status.HTTP_200_OK)
        content = json.loads(resp.content)
        with self.assertRaises(KeyError):
            content['invalid']

    def test_sign_upload_overrides_expiration_date(self):
        resp = self.client.post('/s3/sign/', self.policy_document, format='json')
        policy_decoded = json.loads(resp.content)['policy_decoded']
        expiration = datetime.datetime.strptime(policy_decoded['expiration'], '%Y-%m-%dT%H:%M:%SZ')
        expected_expiration_before = datetime.datetime.today() + datetime.timedelta(300 + 1)
        self.assertLess(expiration, expected_expiration_before)

    def test_sign_upload_preserves_conditions(self):
        resp = self.client.post('/s3/sign/', self.policy_document, format='json')
        policy_decoded = json.loads(resp.content)['policy_decoded']
        self.assertEquals(policy_decoded['conditions'], self.policy_document['conditions'])

    @unittest.expectedFailure
    def test_that_disallowed_bucket_returns_expected_error(self):
        # The view needs to be fixed, so that the uploader gets a message it
        # can reasonably present
        self.policy_document['conditions'][1]['bucket'] = 'secret-bucket'
        resp = self.client.post('/s3/sign/', self.policy_document, format='json')
        self.assertEquals(resp.status_code, status.HTTP_403_FORBIDDEN)
        expected = {'invalid': True, 'errors': {'conditions.bucket': ['Bucket not allowed']}}
        self.assertEquals(json.loads(resp.content), expected)

    @unittest.expectedFailure
    def test_that_disallowed_acl_returns_expected_error(self):
        # The view needs to be fixed, so that the uploader gets a message it
        # can reasonably present
        self.policy_document['conditions'][0]['acl'] = 'public-read'
        resp = self.client.post('/s3/sign/', self.policy_document, format='json')
        self.assertEquals(resp.status_code, status.HTTP_403_FORBIDDEN)
        expected = {'invalid': True, 'errors': {'conditions.acl': ["ACL should be 'private'"]}}
        self.assertEquals(json.loads(resp.content), expected)

FineSignPolicyViewTest = override_settings(**FineSignPolicyViewTest.override_settings)(FineSignPolicyViewTest)


class FineSignPolicyViewSessionAuthTest(APITestCase):
    from drf_to_s3.views import FineSignPolicyView
    urls = patterns('',
        url(r'^s3/sign/$', FineSignPolicyView.as_view()),
    )
    override_settings = {
        'AWS_UPLOAD_SECRET_ACCESS_KEY': '12345',
        'AWS_UPLOAD_BUCKET': 'my-bucket',
    }

    @establish_session
    def test_that_sign_upload_accepts_hashed_session_key(self):
        import hashlib
        self.assertGreater(len(self.session_key), 0)
        prefix = hashlib.md5(self.session_key).hexdigest()
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
        resp = self.client.post('/s3/sign/', self.policy_document, format='json')
        self.assertEquals(resp.status_code, status.HTTP_200_OK)
        content = json.loads(resp.content)
        with self.assertRaises(KeyError):
            content['invalid']

    @unittest.expectedFailure
    @establish_session
    def test_that_sign_upload_without_hashed_session_key_fails(self):
        # FIXME This needs to construct a proper response with 'error' in it
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
        resp = self.client.post('/s3/sign/', self.policy_document, format='json')
        self.assertEquals(resp.status_code, status.HTTP_403_FORBIDDEN)
        content = json.loads(resp.content)
        self.assertTrue(content['invalid'])
        self.assertTrue(content['error'].startswith('Key should start with '))

FineSignPolicyViewSessionAuthTest = override_settings(**FineSignPolicyViewSessionAuthTest.override_settings)(FineSignPolicyViewSessionAuthTest)


class FineUploaderSettingsTest(APITestCase):

    @override_settings(AWS_UPLOAD_SECRET_ACCESS_KEY='1451')
    def test_that_secret_key_pulls_from_settings(self):
        from drf_to_s3.views import FineSignPolicyView
        view = FineSignPolicyView()
        self.assertEquals(view.get_aws_secret_access_key(), '1451')
