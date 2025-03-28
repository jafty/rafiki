# accounts/forms.py
from django.contrib.auth.models import User
from django import forms


class UsernameForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username']
