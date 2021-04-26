import re
from django import forms
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from .models import UserProfile


class RegistrationForm(forms.Form):
	username = forms.RegexField(regex=r'^\w+$', widget=forms.TextInput(attrs=dict(required=True, max_length=30)), label=_("Pseudo"), error_messages={ 'invalid': _("Ce champ ne doit pas contenir de caractères exotiques") })
	email = forms.EmailField(widget=forms.TextInput(attrs=dict(required=True, max_length=30)), label=_("Adresse mail"))
	password1 = forms.CharField(widget=forms.PasswordInput(attrs=dict(required=True, max_length=30, render_value=False)), label=_("Mot de passe"))
	password2 = forms.CharField(widget=forms.PasswordInput(attrs=dict(required=True, max_length=30, render_value=False)), label=_("Confirmation du mot de passe"))

	def clean_username(self):
		try:
			user = User.objects.get(username__iexact=self.cleaned_data['username'])
		except User.DoesNotExist:
			return self.cleaned_data['username']
		raise forms.ValidationError(_("Ce nom d'utilisateur est déjà pris."))
 
	def clean(self):
		if 'password1' in self.cleaned_data and 'password2' in self.cleaned_data:
			if self.cleaned_data['password1'] != self.cleaned_data['password2']:
				raise forms.ValidationError(_("Les deux mots de passe ne correspondent pas"))
		return self.cleaned_data


class UserProfileForm(forms.ModelForm):
	class Meta:
		model = UserProfile
		fields = ('profile_pic', 'bio', 'age')
		labels = {
			'profile_pic': _('Photo de profil :'),
			'age': _('Âge :'),
			'bio': _('Bio :'),
		}

