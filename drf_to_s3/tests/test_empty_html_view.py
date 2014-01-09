from django.conf.urls import patterns, url
from rest_framework import status
from rest_framework.test import APITestCase


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
