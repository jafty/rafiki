from django.test import TestCase
from django.contrib.auth.models import User
from .models import Event, Participation
from unittest.mock import Mock 
from datetime import datetime, timedelta

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
    
    def test_can_manage_if_organizer(self):
        """
        Given an event and a user
        When the user is the organizer
        Then the user can manage the event
        """
        self.assertTrue(self.event.can_manage(self.organizer))

    def test_cannot_manage_if_not_organizer(self):
        """
        Given an event and a user
        When the user is not the organizer
        Then the user can not manage the event
        """
        self.assertFalse(self.event.can_manage(self.participant))


class ParticipationUnitTests(TestCase):
    def setUp(self):
        self.participant = User.objects.create(username="participant")
        self.organizer = User.objects.create(username="organizer")
        self.event = Event.objects.create(
            title="Test Event",
            description="This is a test event",
            organizer=self.organizer,
            location="123 Test Street",
            date=datetime.now() + timedelta(days=1),
        )
        self.participation = Participation.objects.create(
            event=self.event,
            user=self.participant
        )

    def test_accept_participant(self):
        """
        Given a user and a participation
        When the participation is accepted
        Then participation can only be accepted
        """
        self.participation.accept_participant()
        self.assertTrue(self.participation.is_accepted())
        self.assertFalse(self.participation.is_pending())
        self.assertFalse(self.participation.is_rejected())

    def test_reject_participant(self):
        """
        Given a user and a participation
        When the participation is rejected
        Then participation status is rejected
        """
        self.participation.reject_participant()
        self.assertTrue(self.participation.is_rejected())
        self.assertFalse(self.participation.is_accepted())
        self.assertFalse(self.participation.is_pending())

    def test_new_participant(self):
        """
        Given a user and a participation
        When the user just asks for participation
        Then participation status is pending
        """
        self.assertTrue(self.participation.is_pending())
        self.assertFalse(self.participation.is_accepted())
        self.assertFalse(self.participation.is_rejected())
    
    def test_organizer_cannot_join(self):
        """
        Given a user and a participation
        When the user is the organizer
        Then the participation cannot be created
        """
        with self.assertRaises(ValueError):
            Participation.objects.create(event=self.event, user=self.organizer)

        


