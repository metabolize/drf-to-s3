import datetime, json, mock, unittest
from django.conf.urls import patterns, url
from django.test.utils import override_settings
from rest_framework import status
from rest_framework.test import APITestCase


@override_settings(
    AWS_UPLOAD_SECRET_ACCESS_KEY='12345',
    AWS_UPLOAD_BUCKET='my-upload-bucket',
    AWS_UPLOAD_PREFIX_FUNC=lambda x: 'uploads',
    AWS_STORAGE_BUCKET_NAME='my-storage-bucket',
    APPEND_SLASH=False # Work around a Django bug: https://code.djangoproject.com/ticket/21766
)
class TestCompletionViewWithoutAccessControl(APITestCase):
    '''
    This test suite uses a static prefix function to simply
    test things that don't involve access control.

    '''
    from drf_to_s3.views import fine_uploader_views
    urls = patterns('',
        url(r'^s3/uploaded$', fine_uploader_views.FineUploadCompletionView.as_view()),
    )

    @mock.patch('drf_to_s3.s3.copy')
    def test_that_upload_notification_returns_success(self, copy):
        notification = {
            'bucket': 'my-upload-bucket',
            'key': 'uploads/foo/bar/baz',
            'uuid': '12345',
            'name': 'baz',
            'etag': '67890',
        }
        resp = self.client.post('/s3/uploaded', notification)
        self.assertEquals(resp.status_code, status.HTTP_200_OK)
        self.assertEquals(len(resp.content), 0)

    @mock.patch('drf_to_s3.s3.copy')
    @mock.patch('uuid.uuid4')
    def test_that_upload_notification_copies_to_new_key(self, uuid4, copy):
        uuid4.return_value = new_key = 'abcde'
        notification = {
            'bucket': 'my-upload-bucket',
            'key': 'uploads/foo/bar/baz',
            'uuid': '12345',
            'name': 'baz',
            'etag': '67890',
        }
        self.client.post('/s3/uploaded', notification)
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
            'key': 'uploads/foo/bar/baz',
            'uuid': '12345',
            'name': 'baz.txt',
            'etag': '67890',
        }
        self.client.post('/s3/uploaded', notification)
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
            'key': 'uploads/foo/bar/baz',
            'uuid': '12345',
            'name': 'baz.txt',
            'etag': '67890',
        }
        resp = self.client.post('/s3/uploaded', notification)
        self.assertEquals(resp.status_code, status.HTTP_200_OK) # for IE9/IE3
        content = json.loads(resp.content)
        self.assertEquals(content['error'], 'Invalid key or bad ETag')

    def test_that_upload_notification_returns_error_for_invalid_data(self):
        notification = {
            'key': 'uploads/foo/bar/baz',
            'uuid': '12345',
            'name': 'baz.txt',
            'etag': '67890',
        }
        resp = self.client.post('/s3/uploaded', notification)
        self.assertEquals(resp.status_code, status.HTTP_200_OK) # for IE9/IE3
        content = json.loads(resp.content)
        expected_error = 'Unable to complete your request. Errors with bucket'

        self.assertEquals(content['error'], expected_error)

@override_settings(
    AWS_UPLOAD_SECRET_ACCESS_KEY='12345',
    AWS_UPLOAD_BUCKET='my-upload-bucket',
    AWS_STORAGE_BUCKET_NAME='my-storage-bucket',
    APPEND_SLASH=False # Work around a Django bug: https://code.djangoproject.com/ticket/21766
)
class TestCompletionViewSessionAuth(APITestCase):
    from drf_to_s3.views import fine_uploader_views
    urls = patterns('',
        url(r'^s3/uploaded$', fine_uploader_views.FineUploadCompletionView.as_view()),
    )

    def setUp(self):
        from .util import get_user_model
        self.username = 'frodo'
        self.password = 'shire1234'
        user = get_user_model().objects.create_user(
            username=self.username,
            password=self.password
        )

    @mock.patch('drf_to_s3.s3.copy')
    def test_that_upload_notification_with_hashed_session_key_returns_success(self, copy):
        self.client.login(
            username=self.username,
            password=self.password
        )        
        prefix = self.username
        notification = {
            'bucket': 'my-upload-bucket',
            'key': prefix + '/foo/bar/baz',
            'uuid': '12345',
            'name': 'baz',
            'etag': '67890',
        }
        resp = self.client.post('/s3/uploaded', notification)
        self.assertEquals(resp.status_code, status.HTTP_200_OK)
        self.assertEquals(len(resp.content), 0)

    def test_that_upload_notification_without_prefix_fails(self):
        self.client.login(
            username=self.username,
            password=self.password
        )
        notification = {
            'bucket': 'my-upload-bucket',
            'key': 'foo/bar/baz',
            'uuid': '12345',
            'name': 'baz',
            'etag': '67890',
        }
        resp = self.client.post('/s3/uploaded', notification)
        self.assertEquals(resp.status_code, status.HTTP_200_OK) # for IE9/IE3
        content = json.loads(resp.content)
        self.assertTrue(content['error'].startswith('Key should start with'))

    def test_that_upload_notification_without_login_fails(self):
        prefix = self.username
        notification = {
            'bucket': 'my-upload-bucket',
            'key': prefix + '/foo/bar/baz',
            'uuid': '12345',
            'name': 'baz',
            'etag': '67890',
        }
        resp = self.client.post('/s3/uploaded', notification)
        self.assertEquals(resp.status_code, status.HTTP_200_OK) # for IE9/IE3
        content = json.loads(resp.content)
        self.assertEquals(content['error'], 'Log in before uploading')


@override_settings(
    AWS_UPLOAD_SECRET_ACCESS_KEY='12345',
    AWS_UPLOAD_BUCKET='my-upload-bucket',
    AWS_STORAGE_BUCKET_NAME='my-storage-bucket',
    APPEND_SLASH=False # Work around a Django bug: https://code.djangoproject.com/ticket/21766
)
class TestCompletionViewSessionAuth(APITestCase):
    from drf_to_s3.views import api_client_views
    urls = patterns('',
        url(r'^s3/api_uploaded$', api_client_views.APIUploadCompletionView.as_view())
    )

    def setUp(self):
        from .util import get_user_model
        self.username = 'frodo'
        self.password = 'shire1234'
        user = get_user_model().objects.create_user(
            username=self.username,
            password=self.password
        )
        self.client.login(
            username=self.username,
            password=self.password
        )

    @mock.patch('drf_to_s3.s3.copy')
    def test_that_api_upload_notification_returns_success(self, copy):
        prefix = self.username
        notification = {
            'key': prefix + '/foo/bar/baz',
            'filename': 'baz',
        }
        resp = self.client.post('/s3/api_uploaded', notification)
        self.assertEquals(resp.status_code, status.HTTP_200_OK)
        self.assertEquals(len(resp.content), 0)

    def test_that_api_upload_notification_returns_error_for_invalid_data(self):
        notification = {
            'name': 'baz.txt',
        }
        resp = self.client.post('/s3/api_uploaded', notification)
        self.assertEquals(resp.status_code, status.HTTP_400_BAD_REQUEST) 
        content = json.loads(resp.content)
        self.assertEquals(len(content.keys()), 2)

    @mock.patch('drf_to_s3.s3.copy')
    def test_that_api_upload_notification_returns_error_for_nonexistent_key(self, copy):
        from drf_to_s3 import s3
        copy.side_effect = s3.ObjectNotFoundException
        prefix = self.username
        notification = {
            'key': prefix + '/foo/bar/baz',
            'filename': 'baz.txt',
        }
        resp = self.client.post('/s3/api_uploaded', notification)
        self.assertEquals(resp.status_code, status.HTTP_400_BAD_REQUEST)
        content = json.loads(resp.content)
        self.assertEquals(content['detail'], 'Invalid key or bad ETag')
