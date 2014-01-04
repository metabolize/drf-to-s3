from django.conf.urls import patterns, url
from drf_to_s3 import views

urlpatterns = patterns('',
    url(r'^sign/$', views.FineSignPolicyView.as_view()),
    url(r'^empty_html/$', views.empty_html),
)
