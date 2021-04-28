import re
from django import forms
from django.contrib.auth.models import User
from .models import Event
from django.utils.translation import ugettext_lazy as _


class EventForm(forms.ModelForm):

	class Meta:
		model = Event
		fields = {
			"name": _("Nom *"),
			"picture": _("Photo"),
			"address": _("Adresse *"),
			"hidden": _("Événement privé ?"),
			"description": _("Description"),
		}
