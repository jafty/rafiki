from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from events.models import Event, Notification, ParticipationList
from .models import UserProfile
from datetime import datetime
from events.models import Event
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from .forms import RegistrationForm, UserProfileForm
from django.contrib.auth.decorators import login_required


def register(request):
	if request.method == "POST":
		form = RegistrationForm(request.POST)
		if form.is_valid():
			user = User.objects.create_user(
				username=form.cleaned_data["username"],
				password=form.cleaned_data["password1"],
				email=form.cleaned_data["email"],
			)
			return redirect("profile", username=request.user.username)
	else:
		form = RegistrationForm()
	return render(request, "home/register.html", {"form":form})


@login_required
def profile(request, username):
	my_profile = False
	user = get_object_or_404(User, username=username)
	if user == request.user:
		my_profile = True
	profile = get_object_or_404(UserProfile, user=user)
	org_events = Event.objects.filter(author=user)
	participations = ParticipationList.objects.filter(member=user)
	context = {
		"profile" : profile,
		"org_events" : org_events,
		"participations" : participations,
		"my_profile" : my_profile,
	}
	return render(request, "home/profile.html", context)


@login_required
def edit_profile(request):
	profile = get_object_or_404(UserProfile, user=request.user)
	if request.method == "POST":
		profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)
		if profile_form.is_valid():
			profile = profile_form.save()
			return redirect("profile", username=request.user.username)
	else:
		profile_form = UserProfileForm(instance=profile)
	return render(request, "home/edit_profile.html", {"profile_form":profile_form})