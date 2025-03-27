# accounts/urls.py
from django.urls import path
from .views import complete_social_signup

urlpatterns = [
    path('complete-signup/', complete_social_signup, name='complete_social_signup'),
]
