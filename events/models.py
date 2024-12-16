from django.db import models
from django.contrib.auth.models import User

class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateTimeField()
    location = models.CharField(max_length=255)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="organized_events")
    participants = models.ManyToManyField(User, related_name="participating_events", blank=True)
    is_location_hidden = models.BooleanField(default=True)

    def can_view_location(self, user):
        """Checks if an user can see the address"""
        return user in self.participants.all() or user == self.organizer

    def accept_participant(self, user):
        """Allow the event organizer to accept a participant"""
        return None
    

class Testimonial(models.Model):
    pass