from django.conf import settings
from django.conf.urls import include, patterns, url
from django.contrib.auth.signals import user_logged_in
from django.test import TestCase
from django.test.utils import override_settings
from rest_framework.test import APITestCase


urlpatterns = patterns('',
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
)

class TestLogin(TestCase):
    urls = __name__ # Work around a Django bug: https://code.djangoproject.com/ticket/21766

    def setUp(self):
        from .util import get_user_model
        self.username = 'frodo'
        self.password = 'shire1234'
        user = get_user_model().objects.create_user(
            username=self.username,
            password=self.password
        )

    def test_login_view_does_not_set_upload_prefix_cookie_by_default(self):
        data = {
            'username': self.username,
            'password': self.password,
        }
        resp = self.client.post('/api-auth/login/', data)
        self.assertNotIn('upload_prefix', resp.cookies)

    @override_settings(
        MIDDLEWARE_CLASSES=settings.MIDDLEWARE_CLASSES + ('drf_to_s3.middleware.UploadPrefixMiddleware',)
    )
    def test_login_view_sets_upload_prefix_cookie(self):
        data = {
            'username': self.username,
            'password': self.password,
        }
        resp = self.client.post('/api-auth/login/', data)
        self.assertEquals(resp.cookies['upload_prefix'].value, self.username)

    @override_settings(
        MIDDLEWARE_CLASSES=settings.MIDDLEWARE_CLASSES + ('drf_to_s3.middleware.UploadPrefixMiddleware',),
        UPLOAD_PREFIX_COOKIE_NAME='my-app-prefix-cookie',
    )
    def test_login_view_honors_cookie_name_setting(self):
        data = {
            'username': self.username,
            'password': self.password,
        }
        resp = self.client.post('/api-auth/login/', data)
        self.assertNotIn('upload_prefix', resp.cookies)
        self.assertEquals(resp.cookies['my-app-prefix-cookie'].value, self.username)
