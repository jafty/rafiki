from django.conf.urls import url
from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
	path("register/", views.register, name='register'),
	path("login/", auth_views.LoginView.as_view(), name='login'),
	path("edit_profile/", views.edit_profile, name='edit_profile'),
	path("<int:pk>", views.profile, name='profile'),
	path("my_profile/", views.my_profile, name='my_profile'),
]