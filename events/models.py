from django.db import models
from django import forms
from django.contrib.auth.models import User
from datetime import datetime
from django.utils.text import slugify
from django.utils.timezone import now
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, default='avatars/default.jpg')
    description = models.TextField(blank=True, null=True, help_text="Parlez un peu de vous.")
    birth_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(default=now)
    slug = models.SlugField(unique=True, blank=True)

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
        fields = ['avatar', 'description', 'birth_date']

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))

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
    is_location_hidden = models.BooleanField(default=True)
    location = models.CharField(max_length=255)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="organizers")
    image = models.ImageField(upload_to='event_images/', blank=True, null=True, default="event_images/default-rafiki.jpg")

    def can_manage(self, user):
        return self.organizer == user

    def __str__(self):
        return self.title

class EventForm(forms.ModelForm):

    date = forms.CharField(
        label="Date (DD/MM/YYYY)",
        widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY'}),
    )

    class Meta:
        model = Event
        fields = ['title', 'description', 'date', 'location', 'is_location_hidden', 'image']

    def clean_date(self):
        date_str = self.cleaned_data['date']
        try:
            return datetime.strptime(date_str, "%d/%m/%Y")
        except ValueError:
            raise forms.ValidationError("Le format de la date doit être DD/MM/YYYY.")


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

    def __str__(self):
        return f"{self.user.username} <-> {self.event.title}"

    def accept_participant(self):
        self.status = self.ACCEPTED
        self.save()

    def reject_participant(self):
        self.status = self.REJECTED
        self.save()

    def is_accepted(self):
        return self.status == self.ACCEPTED

    def is_rejected(self):
        return self.status == self.REJECTED

    def is_pending(self):
        return self.status == self.PENDING

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
            'placeholder': "Écrivez un message à l'organisateur...",
            'rows': 3,
            'class': 'form-control'
        }),
        label="Message (optionnel)"
    )

    class Meta:
        model = Participation
        fields = ['message']
