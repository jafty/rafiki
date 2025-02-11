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
            return redirect('event_list')
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
    # STRIPE HANDLING
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

    # COMPLETED CHECKOUT ACTIONS
    if stripe_event['type'] == "checkout.session.completed":
        session = stripe_event['data']['object']
        user_id = session['metadata']['user_id']
        event_id = session['metadata']['event_id']
        message = session['metadata']['message']
        user = User.objects.get(id=user_id)
        event = Event.objects.get(id=event_id)
        payment_intent = stripe.PaymentIntent.retrieve(session['payment_intent'])
        if payment_intent["status"] == "requires_capture":
            Participation.objects.get_or_create(
                event=event,
                user=user,
                message=message,  # Enregistre le message
                status=Participation.PENDING,
                stripe_payment_intent=session['payment_intent'],
            )
            notification_exists = Notification.objects.filter(
                user=event.organizer,
                event=event,
                is_read=False
            ).exists()
            print("Before not notification_exists")
            if not notification_exists:
                print("before notify_organizer")
                event.notify_organizer()
    return JsonResponse({"status": "success"}, status=200)


@login_required
def event_payment(request, event_id):
    """ Gère l'inscription et le paiement pour un événement """
    user = request.user
    event = get_object_or_404(Event, id=event_id)

    if request.method == "POST":
        form = ParticipationForm(request.POST)
        if form.is_valid():
            message = form.cleaned_data.get('message')

            # Créer la session Stripe pour le paiement
            session_params = event.get_stripe_session_params()
            session = stripe.checkout.Session.create(
                **session_params,
                metadata={
                    'user_id': user.id,
                    'event_id': event.id,
                    'message': message,  
                }
            )

            # Sauvegarde immédiate de la participation comme "acceptée"
            Participation.objects.create(
                event=event,
                user=user,
                message=message
            )

            return redirect(session.url)  # Redirection vers Stripe Checkout
    else:
        form = ParticipationForm()

    return redirect('event_detail', event_id=event.id)


def event_detail(request, event_id):
    user = request.user if request.user.is_authenticated else None
    event = get_object_or_404(Event, id=event_id)
    participations = Participation.objects.filter(event=event, status=Participation.ACCEPTED)

    participation = None
    is_accepted = False
    is_pending = False
    is_rejected = False
    location = event.location

    if user:
        participation = Participation.objects.filter(user=user, event=event).first()
        is_accepted = participation.is_accepted() if participation else False
        is_pending = participation.is_pending() if participation else False
        is_rejected = participation.is_rejected() if participation else False

        # Masquer l'adresse si l'utilisateur n'est pas accepté et n'est pas l'organisateur
        if not is_accepted and not event.can_manage(user) and event.is_location_hidden:
            location = "Adresse masquée"

    if request.method == "POST":
        if not user:
            return redirect('login')  # Redirige les utilisateurs non connectés vers la page de connexion
        form = ParticipationForm(request.POST)
        if user and is_pending:
            # Si l'utilisateur a une participation en attente, on le renvoie vers Stripe
            session_params = event.get_stripe_session_params()
            session = stripe.checkout.Session.create(
                **session_params,
                metadata={
                    'user_id': user.id,
                    'event_id': event.id,
                    'message': "",  
                }
            )
            return redirect(session.url)

    else:
        form = ParticipationForm() if user else None

    return render(request, 'events/event_detail.html', {
        'event': event,
        'participations': participations,
        'can_manage': event.can_manage(user) if user else False,
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
    can_edit = False
    participations = Participation.objects.filter(
        user=profile.user,
        status=Participation.ACCEPTED,
    )
    if profile.can_edit(user):
        # Profil public
        can_edit = True
        # Profil privé
    organized_events = Event.objects.filter(organizer=profile_user)
    return render(request, 'events/profile.html', {
        'can_edit': can_edit,
        'profile': profile,
        'participations': participations,
        'organized_events': organized_events,
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


def event_list(request):
    events = [event for event in Event.objects.all() if event.is_joinable()]
    events = sorted(events, key=lambda event: event.date)
    return render(request, 'events/event_list.html', {'events': events})

def featured_event(request):
    return redirect('event_detail', event_id="1")

def event_list_fr(request):
    events = [event for event in Event.objects.all() if event.is_joinable()]
    events = sorted(events, key=lambda event: event.date)
    return render(request, 'events/event_list_fr.html', {'events': events})


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
            render(request, 'events/edit_event.html', {'form': form, 'event': event})
    else:
        form = EventForm(initial={
            'title': event.title,
            'description': event.description,
            'location': event.location,
            'date': event.date,  # Pré-remplit le champ date
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
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.profile.consent_date = timezone.now()
            login(request, user)
            
            # Redirection vers l'événement s'il y a un "next"
            next_url = request.GET.get('next', None)
            if next_url:
                return redirect(next_url)

            return redirect('edit_profile', username=user.username)
    else:
        form = CustomUserCreationForm()

    return render(request, 'accounts/register.html', {'form': form})



@login_required
def notifications(request):
    # Récupère les notifications de l'utilisateur
    notifications = request.user.notifications.all().order_by('-created_at')
    # Marque toutes les notifications comme lues
    notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'events/notifications.html', {'notifications': notifications})


def stripe_success(request):
    return render(request, 'events/stripe_success.html')


def stripe_cancel(request):
    return render(request, 'events/stripe_cancel.html')
