from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from .models import Event
from .forms import EventForm
from django.urls import path

# Vues pour le modèle Event

@login_required
def create_event(request):
    """Create a new event"""
    if request.method == "POST":
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            return redirect('event_detail', event_id=event.id)
    else:
        form = EventForm()
    return render(request, 'events/create_event.html', {'form': form})

@login_required
def event_detail(request, event_id):
    """See event details"""
    event = get_object_or_404(Event, id=event_id)
    can_view_location = event.can_view_location(request.user)
    return render(request, 'events/event_detail.html', {
        'event': event,
        'can_view_location': can_view_location
    })

@login_required
def join_event(request, event_id):
    """Allow to join events."""
    event = get_object_or_404(Event, id=event_id)
    if request.user != event.organizer:
        event.participants.add(request.user)
        return redirect('event_detail', event_id=event.id)
    else:
        return HttpResponseForbidden("Vous ne pouvez pas rejoindre votre propre événement.")