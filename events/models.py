from django.db import models
from django import forms
from django.contrib.auth.models import User
from datetime import datetime
from django.utils.text import slugify
from django.utils.timezone import now
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
import stripe.error
from rafiki import settings
from django.core.mail import send_mail
from django.core.validators import RegexValidator
import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, default='avatars/default.jpg')
    description = models.TextField(blank=True, null=True, help_text="Parlez un peu de vous.")
    birth_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(default=now)
    slug = models.SlugField(unique=True, blank=True)
    consent_date = models.DateTimeField(null=True, blank=True, default=None)
    is_certified = models.BooleanField(default=False)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    centers_of_interest = models.TextField(blank=True, null=True, help_text="Qu'appréciez-vous ?")

    def get_age(self, today_date):
        if not self.birth_date:
            return None
        return today_date.year - self.birth_date.year - ((today_date.month, today_date.day) < (self.birth_date.month, self.birth_date.day))

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.user.username)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Profil de {self.user.username}"

    def can_edit(self, user):
        return user == self.user

class UserProfileForm(forms.ModelForm):
    birth_date = forms.DateField(
        required=False,
        input_formats=['%d/%m/%Y'],
        widget=forms.TextInput(attrs={
            'placeholder': 'JJ/MM/AAAA',
        }),
        label="Date de naissance"
    )
    class Meta:
        model = UserProfile
        fields = ['avatar', 'description', 'birth_date', 'city', 'country', 'centers_of_interest']

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    consent = forms.BooleanField(
        label="J'accepte les <a href='/cgu/' target='_blank'>Conditions Générales d'Utilisation</a> et la <a href='/confidentialite/' target='_blank'>Politique de Confidentialité</a>.",
        required=True,
    )
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Cette adresse e-mail est déjà utilisée. Veuillez en choisir une autre.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateTimeField()
    time = models.CharField(
        max_length=6,
        validators=[
            RegexValidator(
                regex=r'^([01]\d|2[0-3]):([0-5]\d)$',
                message="L'heure doit être au format HH:MM (24 heures)."
            )
        ],
        help_text="Veuillez entrer l'heure au format HH:MM."
    )
    is_location_hidden = models.BooleanField(default=True)
    location = models.CharField(max_length=255)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="organizers")
    image = models.ImageField(upload_to='event_images/', blank=True, null=True, default="event_images/default-rafiki.jpg")
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="Prix en euros")
    contact = models.TextField()
    activity_type = models.CharField(max_length=255)


    def can_manage(self, user):
        return self.organizer == user

    def get_price_in_cents(self):
        return int(self.price * 100)

    def is_joinable(self):
        return self.date >= now()

    def notify_organizer(self):
        send_mail(
            f"You have new demands for {self.title}",
            f"You have new demands for {self.title}, please visit your event to\
             handle those requests!<br><br>Team Zanmi",
            settings.DEFAULT_FROM_EMAIL,
            [self.organizer.email],
        )
        print("before notif creation")
        Notification.objects.create(
            user=self.organizer,
            event=self,
            message=f"You have new demands for {self.title}"
        )

    def get_checkout_page(self, user, message):
        """
        Handles generation of checkout when a user wants to join an event
        """
        session_params = self.get_stripe_session_params()
        session = stripe.checkout.Session.create(
            **session_params,
            metadata={
                'user_id': user.id,
                'event_id': self.id,
                'message': message,
            }
        )
        return session.url

    def create_pending_participation(self, message, payment_intent, user_id, requires_capture):
        """
        Creates a pending participation from user and stripe data
        - Prevents duplicates
        - Sends notification to user and organizer
        """
        from .models import Participation, User
        user = User.objects.get(id=user_id)
        if requires_capture:
            participation, created = Participation.objects.get_or_create(
                event=self,
                user=user,
                defaults={
                    'message': message,
                    'stripe_payment_intent': payment_intent,
                    'status': Participation.PENDING,
                }
            )
            if created:
                participation.notify_user(action="pending")
                self.notify_organizer()

    def get_stripe_session_params(self):
        """
        Génère les paramètres nécessaires pour créer une session Stripe Checkout.
        """
        return {
            "payment_method_types": ["card"],
            "line_items": [
                {
                    "price_data": {
                        "currency": "eur",
                        "product_data": {"name": self.title},
                        "unit_amount": self.get_price_in_cents(),
                    },
                    "quantity": 1,
                }
            ],
            "mode": "payment",
            "payment_intent_data": {"capture_method": "manual"},
            "success_url": f"{settings.BASE_URL}/stripe_success/",
            "cancel_url": f"{settings.BASE_URL}/stripe_cancel/",
        }

    def __str__(self):
        return self.title

    # Followings methods do not need tests since they only use native django functions
    def get_accepted_participants(self):
        """Retourne la liste des participants acceptés."""
        return self.participations.filter(status="accepted")

    def get_pending_participants(self):
        """Retourne la liste des participants en attente."""
        return self.participations.filter(status="pending")


class EventForm(forms.ModelForm):

    date = forms.CharField(
        label="Date (DD/MM/YYYY)",
        widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY'}),
    )

    time = forms.CharField(
        label="Heure (de préférence au format HH:MM)",
        widget=forms.TextInput(attrs={'placeholder': 'HH:MM'}),
    )

    class Meta:
        model = Event
        fields = ['title', 'description', 'price', 'date', 'time', 'location', 'activity_type', 'is_location_hidden', 'contact',  'image',]

    def clean_date(self):
        date_str = self.cleaned_data['date']
        try:
            return datetime.strptime(date_str, "%d/%m/%Y")
        except ValueError:
            raise forms.ValidationError("Le format de la date doit être DD/MM/YYYY.")

    def clean_time(self):
        time = self.cleaned_data.get('time', '').strip()
        return time


class Participation(models.Model):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PENDING= "pending"
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (ACCEPTED, 'Accepted'),
        (REJECTED, 'Rejected'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="participations")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="participations")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    message = models.TextField(blank=True, null=True, help_text="Message à l'organisateur")
    stripe_payment_intent = models.CharField(max_length=255, blank=True, null=True, help_text="ID de Stripe PaymentIntent")

    def __str__(self):
        return f"{self.user.username} <-> {self.event.title}"

    def handle_request(self, action, current_user):
        if not self.event.can_manage(current_user):
            raise PermissionError("You can't manage this event.")
        try:
            if action == "reject":
                stripe.PaymentIntent.cancel(self.stripe_payment_intent)
                self.notify_user(action="reject")
                self.status=Participation.REJECTED
                return None
            stripe.PaymentIntent.capture(self.stripe_payment_intent)
            self.notify_user(action="accept")
            self.status=Participation.ACCEPTED
            return None
        except stripe.error.StripeError as e:
            raise RuntimeError(f"Stripe error while processing {action} : {str(e)}")

    def is_accepted(self):
        return self.status == self.ACCEPTED

    def is_rejected(self):
        return self.status == self.REJECTED

    def is_pending(self):
        return self.status == self.PENDING

    def notify_user(self, action=None):
        if action == "reject":
            send_mail(
                f"Your demand for {self.event.title} has been rejected",
                "Sorry, but your request to join {self.event.title} has been rejected.\
                You can ask to join our other events  <br><br>Team Zanmi",
                settings.DEFAULT_FROM_EMAIL,
                [self.user.email]
            )
            Notification.objects.create(
                user=self.user,
                event=self.event,
                message=f"Your demand for {self.event.title} has been rejected"
            )
        elif action == "pending":
            send_mail(
                f"Your demand for {self.event.title} will be reviewed by the organizer. \
                    You will receive all the needed info as soon as he accepts your request. \
                        We do this so we can keep events small and cosy, while making sur everyone will get along!",
                settings.DEFAULT_FROM_EMAIL,
                [self.user.email]
            )
            Notification.objects.create(
                user=self.user,
                event=self.event,
                message=f"Your demand for {self.event.title} will be reviewed by the organizer."
            )
        else:
            send_mail(
                f"Your demand for {self.event.title} has been accepted",
                f"Congrats! You have been accepted to the event {self.event.title}.<br>\
                Here is the location of the event, that you can find on our website : {self.event.location}.<br><br>\
                Here is how to contact the organizer:<br>\
                {self.event.contact}<br><br>Team Zanmi",
                settings.DEFAULT_FROM_EMAIL,
                [self.user.email]
            )
            Notification.objects.create(
                user=self.user,
                event=self.event,
                message=f"Your demand for {self.event.title} has been accepted"
            )

    class Meta:
        unique_together = ('event', 'user')

    def save(self, *args, **kwargs):
        if self.event.organizer == self.user:
            raise ValueError("L'organisateur ne peut pas participer à son propre événement.")
        super().save(*args, **kwargs)

class ParticipationForm(forms.ModelForm):
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'placeholder': "Share a few words about yourself and why you want to join. This helps our organizers ensure a great match between participants and maintain a safe and welcoming environment for everyone.",
            'rows': 3,
            'class': 'form-control'
        }),
        label="Message (optionnel)"
    )

    class Meta:
        model = Participation
        fields = ['message']


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    event = models.ForeignKey('Event', on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(default=now)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:30]}..."
