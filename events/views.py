import stripe
from django.http import JsonResponse  # Pour renvoyer des réponses JSON
from django.views.decorators.csrf import csrf_exempt  # Pour désactiver la vérification CSRF sur des vues spécifiques
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from .models import Event, Participation, EventForm, UserProfile, UserProfileForm, ParticipationForm, CustomUserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.utils.timezone import now
from rafiki import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


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


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    print("stripe_webhook")
    try:
        stripe_event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return JsonResponse({"error": "Invalid payload"}, status=400)
    except stripe.error.SignatureVerificationError:
        return JsonResponse({"error": "Invalid signature"}, status=400)

    # Gestion des événements Stripe
    if stripe_event['type'] == "checkout.session.completed":
        session = stripe_event['data']['object']
        print(session)
        # Récupérer les métadonnées
        user_id = session['metadata']['user_id']
        event_id = session['metadata']['event_id']
        message = session['metadata']['message']

        # Récupérer les objets User et Event
        user = User.objects.get(id=user_id)
        event = Event.objects.get(id=event_id)
        print("supposed to create participation")
        print(user_id)
        # Créer la participation
        payment_intent = stripe.PaymentIntent.retrieve(session['payment_intent'])
        print("PAYMENT INTENT")
        print(payment_intent)
        if payment_intent["status"] == "requires_capture":
            Participation.objects.get_or_create(
                event=event,
                user=user,
                message=message,  # Enregistre le message
                status=Participation.PENDING,
                stripe_payment_intent=session['payment_intent'],
            )

    return JsonResponse({"status": "success"}, status=200)


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
        is_rejected = participation.is_rejected()
    if not is_accepted and not can_manage and event.is_location_hidden:
        location = "Addresse masquée"
    if request.method == "POST":
        form = ParticipationForm(request.POST)
        
        if form.is_valid():
            message = form.cleaned_data.get('message')
            session_params = event.get_stripe_session_params()
            session = stripe.checkout.Session.create(
                **session_params,
                metadata={
                    'user_id': user.id,
                    'event_id': event.id,
                    'message': message,  # Ajoute le message ici
                }
            )
            print("SESSION")
            print(session)
        return redirect(session.url)
    else:
        form = ParticipationForm()

    return render(request, 'events/event_detail.html', {
        'event': event,
        'participations': participations,
        'can_manage': can_manage,
        'is_accepted': is_accepted,
        'location': location,
        'is_pending': is_pending,
        'is_rejected': is_rejected,
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
            try:
                stripe.PaymentIntent.capture(participation.stripe_payment_intent)
                participation.accept_participant()
            except stripe.error.StripeError as e:
                # Gérer les erreurs de capture Stripe
                print(f"Erreur lors de la capture du paiement : {e}")
                return JsonResponse({'error': 'Erreur lors de la capture du paiement.'}, status=400)
        elif action == "reject":
            try:
                stripe.PaymentIntent.cancel(participation.stripe_payment_intent)
                participation.reject_participant()
            except stripe.error.StripeError as e:
                # Gérer les erreurs d'annulation Stripe
                print(f"Erreur lors de l'annulation du paiement : {e}")
                return JsonResponse({'error': 'Erreur lors de l\'annulation du paiement.'}, status=400)
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
    events = [event for event in Event.objects.all() if event.is_joinable()]
    events = sorted(events, key=lambda event: event.date)
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
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('edit_profile', username=user.username)
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})


