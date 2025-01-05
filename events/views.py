from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from .models import Event, Participation, EventForm, UserProfile, UserProfileForm, ParticipationForm
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login

@login_required
def create_event(request):
    if request.method == "POST":
        form = EventForm(request.POST, request.FILES)
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
    if request.method == "POST":
        form = ParticipationForm(request.POST)
        if form.is_valid():
            message = form.cleaned_data.get('message')
            Participation.objects.create(
                event=event,
                user=user,
                status=Participation.PENDING,
                message=message
            )
        return redirect('event_detail', event_id=event.id)
    else:
        form = ParticipationForm()

    return render(request, 'events/event_detail.html', {
        'event': event,
        'participations': participations,
        'can_manage': can_manage,
        'is_accepted': is_accepted,
        'location': location,
        'is_pending': is_pending,
        'form': form,
    })


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
        return redirect('manage_participants', event_id=event.id)
    pending_participants = event.participations.filter(status=Participation.PENDING)
    return render(request, 'events/manage_participants.html', {
        'event': event,
        'pending_participants': pending_participants
    })


@login_required
def profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    profile = get_object_or_404(UserProfile, user=profile_user)
    user = request.user
    participations = Participation.objects.filter(
        user=profile.user,
        status=Participation.ACCEPTED,
    )
    if profile.can_edit(user):
        # Profil public
        can_edit = True
        organized_events = Event.objects.filter(organizer=profile.user)
        return render(request, 'events/profile.html', {
            'can_edit': can_edit,
            'profile': profile,
            'participations': participations,
            'organized_events': organized_events,
        })
    else:
        # Profil privé
        can_edit = False
        return render(request, 'events/profile.html', {
            'can_edit': can_edit,
            'profile': profile,
            'participations': participations,
        })


@login_required
def edit_profile(request, username):
    edited_profile = get_object_or_404(User, username=username).profile
    if not edited_profile.can_edit(request.user):
        return HttpResponseForbidden("Vous ne pouvez pas modifier ce profil.")
    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=edited_profile)
        if form.is_valid():
            form.save()
            return redirect('profile', username=username)
    else:
        form = UserProfileForm(instance=edited_profile)
        if edited_profile.birth_date:
            form.initial['birth_date'] = edited_profile.birth_date.strftime('%d/%m/%Y')
    return render(request, 'events/edit_profile.html', {'form': form})


@login_required
def event_list(request):
    events = Event.objects.all()
    return render(request, 'events/event_list.html', {'events': events})


@login_required
def edit_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    # Vérifie si l'utilisateur est l'organisateur de l'événement
    if not event.can_manage(request.user):
        return HttpResponseForbidden("Vous n'avez pas la permission de modifier cet événement.")

    if request.method == "POST":
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            return redirect('event_detail', event_id=event.id)
    else:
        form = EventForm(instance=event)
        if event.date:
            form.initial['date'] = event.date.strftime('%d/%m/%Y')
    return render(request, 'events/edit_event.html', {'form': form})



def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('edit_profile', username=user.username)
    else:
        form = UserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})
