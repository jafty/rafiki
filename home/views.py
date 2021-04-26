from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from events.models import Event
from profiles.models import UserProfile
from datetime import datetime
from events.models import Event
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from profiles.forms import RegistrationForm, UserProfileForm
from django.contrib.auth.decorators import login_required


from django.http import HttpResponseRedirect


def index(request):
	now = datetime.today()
	events = Event.objects.filter(date__gte=now).order_by("date")
	return render(request, "home/index.html", {"events":events})




