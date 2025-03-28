import stripe
from django.http import JsonResponse  # Pour renvoyer des réponses JSON
from django.views.decorators.csrf import csrf_exempt  # Pour désactiver la vérification CSRF sur des vues spécifiques
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from .models import Event, Participation, EventForm, UserProfile, UserProfileForm, ParticipationForm, CustomUserCreationForm, Notification
from .forms import CertificationForm
from django.core.mail import EmailMessage
from django.contrib.auth.models import User
from django.contrib.auth import login
from rafiki import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
stripe.api_key = settings.STRIPE_SECRET_KEY
from django.utils import timezone
from datetime import date

def landing(request):
    return render(request, 'events/landing.html')


def certification_demand(request):
    if request.method == 'POST':
        form = CertificationForm(request.POST, request.FILES)
        if form.is_valid():
            sender_email = form.cleaned_data['sender_email']
            attachment_id = form.cleaned_data['attachment_id']
            attachment_pic = form.cleaned_data['attachment_pic']
            email = EmailMessage(
                subject="Demande de certification" + " " + request.user.username,
                body=f"Demande de certification de : {request.user}",
                from_email='japhet.situmonana@gmail.com',
                to=['japhet.situmonana@gmail.com'],
                reply_to=[sender_email],
            )
            # TODO: change emails at production
            email.attach(attachment_id.name, attachment_id.read(), attachment_id.content_type)
            email.attach(attachment_pic.name, attachment_pic.read(), attachment_pic.content_type)
            email.send()
            return redirect('/')
    else:
        form = CertificationForm()
    return render(request, 'emails/certification_demand.html', {'form': form})


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

    try:
        stripe_event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return JsonResponse({"error": "Invalid payload"}, status=400)
    except stripe.error.SignatureVerificationError:
        return JsonResponse({"error": "Invalid signature"}, status=400)

    # ✅ Paiement complété
    if stripe_event['type'] == "checkout.session.completed":
        session = stripe_event['data']['object']
        user_id = session['metadata']['user_id']
        event_id = session['metadata']['event_id']

        user = User.objects.get(id=user_id)
        event = Event.objects.get(id=event_id)

        # ✅ Création de la participation (si pas déjà existante)
        participation, created = Participation.objects.get_or_create(
            event=event,
            user=user,
            defaults={'status': Participation.ACCEPTED}
        )

        if created:
            # ✅ Création d'une notification avec l'adresse complète
            Notification.objects.create(
                user=user,
                event=event,
                message=f"You are registered for {event.title}! 🎉\n📍 Address: {event.location}"
            )

            # ✅ Envoi d'un email de confirmation
            subject = f"Confirmation: You are registered for {event.title} 🎉"
            html_message = render_to_string("emails/confirmation_event.html", {
                'user': user,
                'event': event,
                'location': event.location,
                'contact': event.contact
            })
            plain_message = strip_tags(html_message)  # Version texte brut
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message
            )

    return JsonResponse({"status": "success"}, status=200)


@login_required
def event_payment(request, event_id):
    """ Gère l'inscription et le paiement pour un événement """
    user = request.user
    event = get_object_or_404(Event, id=event_id)

    # Créer la session Stripe pour le paiement
    session_params = event.get_stripe_session_params()
    session = stripe.checkout.Session.create(
        **session_params,
        metadata={
            'user_id': user.id,
            'event_id': event.id,
        }
    )

    return redirect(session.url)  # Redirection vers Stripe Checkout



@login_required(login_url='login')
def event_detail(request, event_id):
    # TODO: refacto
    user = request.user
    event = get_object_or_404(Event, id=event_id)
    participations = Participation.objects.filter(event=event, status=Participation.ACCEPTED)

    participation = Participation.objects.filter(user=user, event=event).first()
    is_accepted = participation.is_accepted() if participation else False
    is_pending = participation.is_pending() if participation else False
    is_rejected = participation.is_rejected() if participation else False

    # Masquer l’adresse si l'utilisateur n'est pas accepté et ce n’est pas l’organisateur
    location = event.location
    if not is_accepted and not event.can_manage(user) and event.is_location_hidden:
        location = "Join the event to see the location"

    if request.method == "POST":
        form = ParticipationForm(request.POST)

        # Si l'utilisateur a déjà une participation, on ne crée pas de doublon
        if Participation.objects.filter(user=user, event=event).exists():
            return redirect('event_detail', event_id=event.id)

        if form.is_valid():
            participation = form.save(commit=False)
            participation.user = user
            participation.event = event
            participation.status = Participation.PENDING
            participation.message = form.cleaned_data.get('message', '')
            participation.save()
            event.notify_organizer()
            return redirect('event_payment', event_id=event.id)
    else:
        form = ParticipationForm() if not is_accepted and not is_pending and not is_rejected else None
    return render(request, 'events/event_detail.html', {
        'event': event,
        'participations': participations,
        'can_manage': event.can_manage(user),
        'is_accepted': is_accepted,
        'is_pending': is_pending,
        'is_rejected': is_rejected,
        'form': form,
        'location': location,
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
                participation.notify_user(action="accept")
            except stripe.error.StripeError as e:
                # Gérer les erreurs de capture Stripe
                print(f"Erreur lors de la capture du paiement : {e}")
                return JsonResponse({'error': 'Erreur lors de la capture du paiement.'}, status=400)
        elif action == "reject":
            try:
                stripe.PaymentIntent.cancel(participation.stripe_payment_intent)
                participation.reject_participant()
                participation.notify_user(action="reject")
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
    can_edit = profile_user == user
    age = profile.get_age(date.today())
    participations = Participation.objects.filter(
        user=profile_user,
        status=Participation.ACCEPTED,
    ).select_related('event')
    today = timezone.now()
    upcoming_events = [p for p in participations if p.event.date >= today]
    past_events = [p for p in participations if p.event.date < today]
    organized_events = Event.objects.filter(organizer=profile_user)
    context = {
        'can_edit': can_edit,
        'profile': profile,
        'upcoming_events': upcoming_events,
        'past_events': past_events,
        'organized_events': organized_events,
        'events_attended_count': len(past_events),
        'upcoming_events_count': len(upcoming_events),
        'age': age,
    }
    return render(request, 'events/profile.html', context)


@login_required
def edit_profile(request, username):
    edited_profile = get_object_or_404(User, username=username).profile
    if not edited_profile.can_edit(request.user):
        return HttpResponseForbidden("Vous ne pouvez pas modifier ce profil.")
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=edited_profile)
        if form.is_valid():
            form.save()
            # Redirige vers l'événement avec ID 28 après la mise à jour du profil
            return redirect('event_detail', event_id=28)  # L'ID de l'événement à mettre en avant
    else:
        form = UserProfileForm(instance=edited_profile)

    return render(request, 'events/edit_profile.html', {'form': form})


def event_list(request):
    events = [event for event in Event.objects.all() if event.is_joinable()]
    events = sorted(events, key=lambda event: event.date)
    return render(request, 'events/event_list.html', {'events': events})


def featured_event(request):
    event = get_object_or_404(Event, id=28)
    if event:
        return redirect('event_detail', event_id=event.id)
    return redirect('event_list')  # Si aucun événement valide, rediriger vers la liste (ou autre)


def event_list_fr(request):
    events = [event for event in Event.objects.all() if event.is_joinable()]
    events = sorted(events, key=lambda event: event.date)
    return render(request, 'events/event_list_fr.html', {'events': events})


@login_required
def edit_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if not event.can_manage(request.user):
        return HttpResponseForbidden("Vous n'avez pas la permission de modifier cet événement.")
    if request.method == "POST":
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            return redirect('event_detail', event_id=event.id)
        else:
            render(request, 'events/edit_event.html', {'form': form, 'event': event})
    else:
        form = EventForm(initial={
            'title': event.title,
            'description': event.description,
            'location': event.location,
            'date': event.date,
            'price': event.price,
            'is_location_hidden': event.is_location_hidden,
            'time': event.time,
            'activity_type': event.activity_type,
            'contact': event.contact,
            'image': event.image,
        })
        if event.date:
            form.initial['date'] = event.date.strftime('%d/%m/%Y')
    return render(request, 'events/edit_event.html', {'form': form, 'event': event})


def register(request):
    if request.user.is_authenticated:
        return redirect('event_detail', event_id=28)

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('edit_profile', username=user.username)
    else:
        form = CustomUserCreationForm()

    return render(request, 'accounts/register.html', {'form': form})


@login_required
def notifications(request):
    notifications = request.user.notifications.all().order_by('-created_at')
    notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'events/notifications.html', {'notifications': notifications})


def stripe_success(request):
    return render(request, 'events/stripe_success.html')


def stripe_cancel(request):
    return render(request, 'events/stripe_cancel.html')

