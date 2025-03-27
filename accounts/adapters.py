# accounts/adapters.py
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter  # ← celui-là pour MySocialAccountAdapter
from django.urls import reverse


class CustomAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        user = request.user
        if not user.username:
            return reverse('complete_social_signup')
        return super().get_login_redirect_url(request)


class MySocialAccountAdapter(DefaultSocialAccountAdapter):  # ← ici aussi !
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)

        # On force à laisser vide pour forcer le formulaire plus tard
        user.username = ""
        return user
