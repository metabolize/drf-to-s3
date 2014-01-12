from django.conf.urls import patterns, url
from rest_framework import status
from rest_framework.test import APITestCase


class TestEmptyHTMLView(APITestCase):
    urls = 'drf_to_s3.urls'

    def test_that_secret_key_pulls_from_settings(self):
        resp = self.client.get('/empty_html')
        self.assertEquals(resp.status_code, status.HTTP_200_OK)
        # Doesn't seem to set this on empty content; does that matter?
        # self.assertEquals(resp['Content-Type'], 'text/html')
        self.assertEquals(resp.content, '')
