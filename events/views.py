from django.shortcuts import render
from .models import Event, Notification
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from .models import Event, Notification, ParticipationList
from profiles.models import UserProfile
from django.contrib.auth.models import User
from .forms import EventForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
import urllib.request
from django.http import HttpResponseRedirect
from datetime import datetime
from django.conf import settings
from django.core.mail import EmailMessage
from django.template import Context
from django.template.loader import get_template
from django.http import HttpResponseRedirect
from django.urls import reverse

def event_list(request):
	now = datetime.today()
	events=Event.objects.filter(date__gte=now).order_by('date')
	event_filter=EventFilter(request.GET, queryset=events)
	return render(request, 'home/event_list.html', {'events':events, 'filter':event_filter})


def event_detail(request, pk, asked):
	# TODO: implement form here
	event = get_object_or_404(Event, pk=pk)
	event_author = event.author
	author_profile = get_object_or_404(UserProfile, event_author)
	return render(request, 'home/event_detail.html', {'event':event, 'profile':profile})


"""
Handling posting events
"""
def event_new(request):
	profile = get_object_or_404(UserProfile, user=user)
	if request.method == "POST":
		posted_event(request)
	else:
		form = EventForm()
	return render(request, "home/event_new.html", {"form":form, "profile":"profile"})

def posted_event(request):
	form = EventForm(request.POST, request.FILES or None)
	if form.is_valid():
		event = form.save(commit=False)
		event.price=event.price*100
		event.author = request.user
		event.stripe_user_id = "no_stripe_id"
		list=List.objects.filter(event=event, paid=True)
		event.save()
		return render(request, 'home/my_event.html', {'list':list, 'event':event})
		# TODO: handle not free
"""
/Handling posting events 
"""


@login_required
def edit_event(request, pk):
	profile = get_object_or_404(UserProfile, user=request.user)
	event = get_object_or_404(Event, pk=pk)
	if request.user != event.author:
		return redirect('/')
	if request.method == "POST":
		form = EventForm(request.POST, instance=event)
		if form.is_valid:
			event = form.save()
			return redirect("/")
			# TODO: redirect at the right place
	else:
		form = EventForm(instance=event)
	return render(request, "home/edit_event.html", {"form":form})


@login_required
def delete_event(request, pk):
	event = get_object_or_404(Event, pk=pk)
	if request.user!=event.author:
		return redirect("/")
	else:
		event.delete()
	return HttpResponseRedirect(reverse("profile", username=request.user.username))

@login_required
def ask_event(request, pk):
	event = get_object_or_404(Event, pk=pk)
	Notification.create(
		sender=request.user, 
		receiver=event.author, 
		event=event,
		msg_content=str(request.user.username) + "veut participer à ta soirée " + event.name)
	return redirect('event_detail', event=event, asked=1)


@login_required
def refuse(request, pk, cand):
	candidate=get_object_or_404(User, username=cand)
	event = get_object_or_404(Event, pk=pk)
	Notification.create(
		sender=request.user,
		receiver=candidate,
		event=event,
		msg_content=str(request.user.username) + "a refusé ta participation à" + event.name)
	return redirect("profile", username=request.user.username)


@login_required
def accept(request, pk, cand):
	candidate = get_object_or_404(username=cand)
	event = get_object_or_404(pk=pk)
	Notification.objects.create(
		sender=request.user, 
		receiver=candidate, 
		event=event, 
		msg_content="Vous avez été autorisé à participer à l'évènement.")
	return redirect("profile", username=request.user.username)


@login_required
def notification_list(request):
	notifications = Notification.objects.filter(receiver=request.user)
	return render(request, "home/event_list.html")