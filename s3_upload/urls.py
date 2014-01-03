from django.conf.urls import patterns, url
from s3_upload import views

urlpatterns = patterns('',
    url(r'^sign/$', views.FineUploaderSignUploadPolicyView.as_view()),
    url(r'^empty_html/$', views.empty_html),
)
