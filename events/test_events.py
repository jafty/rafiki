import django
import os
from rafiki import settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rafiki.settings')
django.setup()
from django.test import TestCase
from django.contrib.auth.models import User
from events.models import Event, Participation, UserProfile, Notification
from datetime import datetime, timedelta
from django.utils.timezone import now
from unittest.mock import patch
from unittest import mock


class UserProfileUnitTests(TestCase):
    def setUp(self):
        # User creation
        self.random_user = User.objects.create(username="random_user")
        self.profile_user = User.objects.create(username="participant")
        self.profile = UserProfile.objects.get(user=self.profile_user)

    def test_user_can_edit_his_own_profile(self):
        """
        Given a profile and a user
        When the profile belongs to the user
        Then the user can edit his profile
        """
        self.assertTrue(self.profile.can_edit(self.profile_user))
        self.assertFalse(self.profile.can_edit(self.random_user))


class EventUnitTests(TestCase):
    def setUp(self):
        # User creation
        self.organizer = User.objects.create(username="organizer", email="japhet.situmonana@gmail.com")
        self.participant = User.objects.create(username="participant")
        # Event creation
        self.event = Event.objects.create(
            title=" Test Event 1",
            description="This is a test event 1",
            date= now() + timedelta(days=2),
            location = "Test Location",
            organizer=self.organizer,
            price=10.00,
        )
        self.past_event = Event.objects.create(
            title=" Test Event 1",
            description="This is a test event 1",
            date= now() - timedelta(days=2),
            location = "Test Location",
            organizer=self.organizer,
            price=100.00,
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

    def test_cannot_join_event_if_past_due(self):
        """
        Given an event
        When the event date is anterior to the date of the day
        Then nobody can join the event
        """
        self.assertFalse(self.past_event.is_joinable())
        self.assertTrue(self.event.is_joinable())

    def test_euros_to_cents_conversion(self):
        """
        Given an event
        When the price in euros is converted in centimes
        Then the centime result is 100 times the euros price
        """
        self.assertEqual(self.event.get_price_in_cents(), 1000)
        self.assertEqual(self.past_event.get_price_in_cents(), 10000)

    def test_get_stripe_session_params(self):
        params = self.event.get_stripe_session_params()

        # Vérifie que les paramètres contiennent les clés attendues
        self.assertIn("payment_method_types", params)
        self.assertIn("line_items", params)
        self.assertIn("mode", params)
        self.assertIn("success_url", params)
        self.assertIn("cancel_url", params)

        # Vérifie les valeurs spécifiques
        self.assertEqual(params["payment_method_types"], ["card"])
        self.assertEqual(params["line_items"][0]["price_data"]["unit_amount"], 1000)
        self.assertEqual(params["line_items"][0]["price_data"]["currency"], "eur")
        self.assertEqual(params["line_items"][0]["price_data"]["product_data"]["name"], self.event.title)
        self.assertEqual(params["success_url"], f"{settings.BASE_URL}/stripe_success/")
        self.assertEqual(params["cancel_url"], f"{settings.BASE_URL}/stripe_cancel/")

    @patch('events.models.send_mail')
    def test_notify_organizer(self, mock_send_mail):
        """
        Given a user and an event
        When the user asks to join the event
        Then the event organizer is notified
        """
        self.event.notify_organizer()
        mock_send_mail.assert_called_once_with(
            f"You have new demands for {self.event.title}",
            mock.ANY,
            settings.DEFAULT_FROM_EMAIL,
            [self.event.organizer.email]
        )
        notification = Notification.objects.filter(user=self.organizer, event=self.event, is_read=False).first()
        self.assertIsNotNone(notification)
        self.assertIn(f"new demands for {self.event.title}", notification.message)


class ParticipationUnitTests(TestCase):
    def setUp(self):
        self.participant = User.objects.create(username="participant", email="japhet.situmonana@gmail.com")
        self.organizer = User.objects.create(username="organizer", email="japhet.situmonana@gmail.com")
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


    @patch('events.models.send_mail')
    def test_notify_rejected_user(self, mock_send_mail):
        """
        Given a pending user participation to an event
        When the organizer rejects the user demand
        Then the user is notified of his rejection
        """
        self.participation.notify_user(action='reject')
        mock_send_mail.assert_called_once_with(
            f"Your demand for {self.event.title} has been rejected",
            mock.ANY,
            settings.DEFAULT_FROM_EMAIL,
            [self.participant.email],
        )
        notification = Notification.objects.filter(user=self.participant, event=self.event, is_read=False).first()
        self.assertIsNotNone(notification)
        self.assertIn("rejected", notification.message)


    @patch('events.models.send_mail')
    def test_notify_accepted_user(self, mock_send_mail):
        """
        Given a pending user participation to an event
        When the organizer accepts the user demand
        Then the user is notified of his acceptation
        """
        self.participation.notify_user(action='accept')
        mock_send_mail.assert_called_once_with(
            f"Your demand for {self.event.title} has been accepted",
            mock.ANY,
            settings.DEFAULT_FROM_EMAIL,
            [self.participant.email],
        )
        notification = Notification.objects.filter(user=self.participant, event=self.event, is_read=False).first()
        self.assertIsNotNone(notification)
        self.assertIn("accepted", notification.message)



