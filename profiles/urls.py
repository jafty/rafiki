from django.conf.urls import url
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
	url(r'^register/$', views.register, name='register'),
	url(r'^login/$', auth_views.LoginView.as_view(), name='login'),
	url(r'^edit_profile/$', views.edit_profile, name='edit_profile'),
	url(r'^(?P<username>[\w-]+)/profile$', views.profile, name='profile'),
]