from django.conf.urls import url
from . import views
from django.contrib.auth import views as auth_views


urlpatterns = [
    url(r'^$', views.event_list, name='event_list'),
	url(r'^(?P<pk>[0-9]+)/(?P<asked>[0-1]+)/$', views.event_detail, name='event_detail'),
	url(r'^new/$', views.event_new, name='event_new'),
	url(r'^(?P<pk>[0-9]+)/ask_event$', views.ask_event, name='ask_event'),
	url(r'^notifications/$', views.notification_list, name='notification_list'),
	url(r'^(?P<pk>[0-9]+)/(?P<cand>[\w-]+)/accept$', views.accept, name='accept'),
	url(r'^(?P<pk>[0-9]+)/(?P<cand>[\w-]+)/refuse$', views.refuse, name='refuse'),
	url(r'^(?P<pk>[0-9]+)/edit_event$', views.edit_event, name='edit_event'),
]