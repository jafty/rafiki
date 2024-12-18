from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseForbidden, JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Event, Participation, EventForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login

@login_required
def create_event(request):
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
    user = request.user
    event = get_object_or_404(Event, id=event_id)
    participations = Participation.objects.filter(event=event, status=Participation.ACCEPTED)
    can_manage = event.can_manage(user)
    is_accepted = False
    is_pending = False
    location = event.location
    if Participation.objects.filter(user=user, event=event).exists():
        participation = Participation.objects.get(user=user, event=event)
        is_accepted = participation.is_accepted()
        is_pending = participation.is_pending()
    if not is_accepted and not can_manage and event.is_location_hidden:
        location = "Addresse masquée"
    return render(request, 'events/event_detail.html', {
        'event': event,
        'participations': participations,
        'can_manage': can_manage,
        'is_accepted': is_accepted,
        'location': location,
        'is_pending': is_pending
    })

@login_required
def join_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    try:
        Participation.objects.get_or_create(event=event, user=request.user, status=Participation.PENDING)
    except ValueError as e:
        return HttpResponseForbidden(str(e))
    return redirect('event_detail', event_id=event.id)

@login_required
def manage_participants(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.method == "POST":
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')
        participation = get_object_or_404(Participation, event=event, user_id=user_id)
        if action == "accept":
            participation.accept_participant()
        elif action == "reject":
            participation.reject_participant()
        return redirect('event_detail', event_id=event.id)
    pending_participants = event.participations.filter(status=Participation.PENDING)
    return render(request, 'events/manage_participants.html', {
        'event': event,
        'pending_participants': pending_participants
    })

@login_required
def event_list(request):
    events = Event.objects.all()
    return render(request, 'events/event_list.html', {'events': events})


def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  
            return redirect('event_list')  
    else:
        form = UserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})
