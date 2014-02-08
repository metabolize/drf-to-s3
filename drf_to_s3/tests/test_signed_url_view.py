import os, datetime, json, mock, unittest
from django.conf.urls import patterns, url
from django.test.utils import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

class FineSignedUrlViewTest(APITestCase):
    urls = 'drf_to_s3.urls'
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

    @override_settings(
        AWS_UPLOAD_SECRET_ACCESS_KEY='12345',
        AWS_UPLOAD_ACCESS_KEY_ID='67890',
        AWS_UPLOAD_BUCKET='test-bucket',
    )
    def test_that_view_return_signed_url(self):
        resp = self.client.post('/upload_uri')
        self.assertEquals(resp.status_code, status.HTTP_200_OK)

        content = json.loads(resp.content)

        self.assertIn('upload_uri', content)
        self.assertIn('key', content)
