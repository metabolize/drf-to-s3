import datetime, json, mock, unittest
from django.conf.urls import patterns, url
from django.test.utils import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from .util import establish_session


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
