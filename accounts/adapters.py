# accounts/adapters.py
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.urls import reverse
from allauth.account.adapter import DefaultAccountAdapter


class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        print("populate_user")
        user = super().populate_user(request, sociallogin, data)
        user.username = f"temp_{sociallogin.account.uid[:6]}"
        request.session['is_first_login'] = True
        return user


class CustomAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        print("get_login_redirect_url")
        user = request.user
        if user.username.startswith("temp_"):
            return reverse('complete_social_signup')

        # Redirige vers edit_profile juste après création du compte
        if request.session.pop('is_first_login', False):
            return reverse('edit_profile', kwargs={'username': user.username})

        return reverse('feature_event')  # page par défaut

