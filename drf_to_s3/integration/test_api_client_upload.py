import os
from django.conf.urls import include, patterns, url
from django.test import LiveServerTestCase
from django.test.utils import override_settings
from rest_framework import status
from drf_to_s3.tests.util import create_random_temporary_file
from drf_to_s3.views import api_client_views

class APIUploadTestView(api_client_views.APIUploadCompletionView):
    '''
    Test view for mock api user's work flow. API user should extend the APICompletionView
    and override functions based on their needs.
    '''
    pass

urlpatterns = patterns('',
    url(r'^api/s3/', include('drf_to_s3.urls')),
    url(r'^api/s3/file_uploaded', APIUploadTestView.as_view()),
)

@override_settings(
    AWS_UPLOAD_BUCKET=os.environ.get('AWS_TEST_BUCKET', 'drf-to-s3-test'),
    AWS_STORAGE_BUCKET_NAME=os.environ.get('AWS_TEST_BUCKET', 'drf-to-s3-test'),
    AWS_UPLOAD_ACCESS_KEY_ID=os.environ['AWS_ACCESS_KEY_ID'],
    AWS_UPLOAD_SECRET_ACCESS_KEY=os.environ['AWS_SECRET_ACCESS_KEY']
)
class FineAPITest(LiveServerTestCase):
    
    urls = __name__
    
    def setUp(self):
        from drf_to_s3.tests.util import get_user_model
        self.username = 'frodo'
        self.password = 'shire1234'
        user = get_user_model().objects.create_user(
            username=self.username,
            password=self.password
        )
        self.test_file = create_random_temporary_file()
        self.client.login(username=self.username, password=self.password)

    def tearDown(self):
        os.remove(self.test_file)

    def test_api_upload(self):
        import requests, json

        #STEP1: Get signed_url and upload the file
        resp = self.client.post('/api/s3/upload_uri')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        content = json.loads(resp.content)

        dst_key = content['key']
        upload_uri = content['upload_uri']

        with open(self.test_file, 'r') as f:
            resp = requests.put(upload_uri, data=f.read())
            self.assertEqual(resp.status_code, status.HTTP_200_OK)

        #STEP2: Hit the APIUpload compeletion view
        request_payload = {
            'key': dst_key,
            'filename': 'foobar.jpg',
        }

        resp = self.client.post(
            '/api/s3/file_uploaded',
            data=request_payload
        )

        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEquals(len(resp.content), 0)

