from django.db import models
from django import forms
from django.contrib.auth.models import User
from datetime import datetime

class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateTimeField()
    is_location_hidden = models.BooleanField(default=True)
    location = models.CharField(max_length=255)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="organizers")

    def can_manage(self, user):
        return self.organizer == user


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

    
class EventForm(forms.ModelForm):

    date = forms.CharField(
        label="Date (DD/MM/YYYY)",
        widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY'}),
    )

    class Meta:
        model = Event
        fields = ['title', 'description', 'date', 'location', 'is_location_hidden']

    def clean_date(self):
        date_str = self.cleaned_data['date']
        try:
            return datetime.strptime(date_str, "%d/%m/%Y")
        except ValueError:
            raise forms.ValidationError("Le format de la date doit être DD/MM/YYYY.")