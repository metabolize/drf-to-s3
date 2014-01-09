import datetime, json, mock, unittest
from django.conf.urls import patterns, url
from django.test.utils import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

class FineSignPolicyViewTest(APITestCase):
    from drf_to_s3.views import FineSignPolicyView
    urls = patterns('',
        url(r'^s3/sign/$', FineSignPolicyView.as_view()),
    )
    override_settings = {
        'AWS_UPLOAD_SECRET_ACCESS_KEY': '12345',
        'AWS_UPLOAD_BUCKET': 'my-bucket',
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


class FineUploaderSettingsTest(APITestCase):

    @override_settings(AWS_UPLOAD_SECRET_ACCESS_KEY='1451')
    def test_that_secret_key_pulls_from_settings(self):
        from drf_to_s3.views import FineSignPolicyView
        view = FineSignPolicyView()
        self.assertEquals(view.get_aws_secret_access_key(), '1451')


class TestEmptyHTMLView(APITestCase):
    from drf_to_s3.views import empty_html

    urls = patterns('',
        url(r'^s3/empty_html/$', empty_html),
    )

    def test_that_secret_key_pulls_from_settings(self):
        resp = self.client.get('/s3/empty_html/')
        self.assertEquals(resp.status_code, status.HTTP_200_OK)
        # Doesn't seem to set this on empty content; does that matter?
        # self.assertEquals(resp['Content-Type'], 'text/html')
        self.assertEquals(resp.content, '')


class TestCompletionView(APITestCase):
    from drf_to_s3.views import FineUploadCompletionView
    urls = patterns('',
        url(r'^s3/uploaded/$', FineUploadCompletionView.as_view()),
    )

    override_settings = {
        'AWS_UPLOAD_SECRET_ACCESS_KEY': '12345',
        'AWS_UPLOAD_BUCKET': 'my-upload-bucket',
        'AWS_STORAGE_BUCKET_NAME': 'my-storage-bucket',
    }

    @mock.patch('drf_to_s3.s3.copy')
    def test_that_upload_notification_returns_success(self, copy):
        notification = {
            'bucket': 'my-upload-bucket',
            'key': '/foo/bar/baz',
            'uuid': '12345',
            'name': 'baz',
            'etag': '67890',
        }
        resp = self.client.post('/s3/uploaded/', notification)
        self.assertEquals(resp.status_code, status.HTTP_200_OK)
        self.assertEquals(len(resp.content), 0)

    @mock.patch('drf_to_s3.s3.copy')
    @mock.patch('uuid.uuid4')
    def test_that_upload_notification_copies_to_new_key(self, uuid4, copy):
        uuid4.return_value = new_key = 'abcde'
        notification = {
            'bucket': 'my-upload-bucket',
            'key': '/foo/bar/baz',
            'uuid': '12345',
            'name': 'baz',
            'etag': '67890',
        }
        self.client.post('/s3/uploaded/', notification)
        copy.assert_called_once_with(
            src_bucket=notification['bucket'],
            src_key=notification['key'],
            etag=notification['etag'],
            dst_bucket='my-storage-bucket',
            dst_key=new_key
        )

    @mock.patch('drf_to_s3.s3.copy')
    @mock.patch('uuid.uuid4')
    def test_that_upload_notification_preserves_extension_for_new_key(self, uuid4, copy):
        uuid4.return_value = new_key = 'abcde'
        notification = {
            'bucket': 'my-upload-bucket',
            'key': '/foo/bar/baz',
            'uuid': '12345',
            'name': 'baz.txt',
            'etag': '67890',
        }
        self.client.post('/s3/uploaded/', notification)
        copy.assert_called_once_with(
            src_bucket=notification['bucket'],
            src_key=notification['key'],
            etag=notification['etag'],
            dst_bucket='my-storage-bucket',
            dst_key=new_key + '.txt'
        )

    @mock.patch('drf_to_s3.s3.copy')
    def test_that_upload_notification_returns_error_for_nonexistent_key(self, copy):
        from drf_to_s3 import s3
        copy.side_effect = s3.ObjectNotFoundException
        notification = {
            'bucket': 'my-upload-bucket',
            'key': '/foo/bar/baz',
            'uuid': '12345',
            'name': 'baz.txt',
            'etag': '67890',
        }
        resp = self.client.post('/s3/uploaded/', notification)
        content = json.loads(resp.content)
        self.assertTrue(content['invalid'])
        self.assertEquals(content['error'], 'Invalid key or bad ETag')

TestCompletionView = override_settings(**TestCompletionView.override_settings)(TestCompletionView)
