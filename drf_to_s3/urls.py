from django.conf.urls import patterns, url
from drf_to_s3.views import api_client_views, fine_uploader_views

urlpatterns = patterns('',
    url(r'^upload_uri$', api_client_views.SignedPutURIView.as_view()),
    url(r'^sign$', fine_uploader_views.FineSignPolicyView.as_view()),
    url(r'^empty_html$', fine_uploader_views.empty_html),
)
