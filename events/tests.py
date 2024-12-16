from django.test import TestCase
from django.contrib.auth.models import User
from .models import Event, Testimonial
from unittest.mock import Mock 

class EventUnitTests(TestCase):
    def setUp(self):
        # User creation 
        self.organizer = User.objects.create(username="organizer")
        self.participant = User.objects.create(username="participant")
        # Event creation
        self.event = Event.objects.create(
            title=" Test Event 1",
            description="This is a test event 1",
            date="2024-12-31 18:00",
            location = "Test Location",
            organizer=self.organizer,
        )
    
    def test_can_view_location_as_organizer(self):
        # Test that participant is able to view his own event location
        self.assertTrue(self.event.can_view_location(self.organizer))
    
    def test_can_view_location_as_participant(self):
        # Test that participant is able to view his own event location
        self.event.participants.add(self.participant)
        self.assertTrue(self.event.can_view_location(self.participant))

    def test_cannot_view_location_as_non_participant(self):
        # Test that participant is able to view his own event location
        self.event.participants.add(self.participant)
        self.assertTrue(self.event.can_view_location(self.participant))
    
    def test_organizer_can_accept_user(self):
        # Test that accepted user belongs to the event
        self.event.accept_participant(self.participant)
        self.assertIn(self.participant, self.event.participants)    
