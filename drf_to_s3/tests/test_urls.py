from rest_framework.test import APITestCase


class URLTest(APITestCase):
    from drf_to_s3.urls import urlpatterns
    urls = urlpatterns

    def test_that_import_succeeds(self):
        pass
