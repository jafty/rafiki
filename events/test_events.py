import django
import os
from rafiki import settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rafiki.settings')
django.setup()
from django.test import TestCase
from django.contrib.auth.models import User
from events.models import Event, Participation, UserProfile, Notification
from datetime import datetime, timedelta, date
from django.utils.timezone import now
from unittest.mock import patch
from unittest import mock
from unittest.mock import patch, MagicMock
from django.shortcuts import get_object_or_404
import stripe

class UserProfileUnitTests(TestCase):
    def setUp(self):
        # User creation
        self.random_user = User.objects.create(username="random_user")
        self.profile_user = User.objects.create(username="participant")
        self.profile = UserProfile.objects.get(user=self.profile_user)
        self.today_date = datetime(2025, 3, 28)


    def test_user_can_edit_his_own_profile(self):
        """
        Given a profile and a user
        When the profile belongs to the user
        Then the user can edit his profile
        """
        self.assertTrue(self.profile.can_edit(self.profile_user))
        self.assertFalse(self.profile.can_edit(self.random_user))

    def test_user_is_29(self):
        """
        Given a profile
        When the profile is born in 19/09/1995 and the date is 28/03/2025
        Then 29 is calculated
        """
        self.user_29 = User.objects.create(username="user_29")
        self.profile_29 = UserProfile.objects.get(user=self.user_29)
        self.profile_29.birth_date=date(1995, 9, 19)
        self.assertEqual(self.profile_29.get_age(self.today_date), 29)

    def test_user_is_39(self):
        """
        Given a profile
        When the profile is born in 19/09/1985 and the date is 28/03/2025
        Then 39 is calculated
        """
        self.user_39 = User.objects.create(username="user_39")
        self.profile_39 = UserProfile.objects.get(user=self.user_39)
        self.profile_39.birth_date=date(1985, 9, 19)
        self.assertEqual(self.profile_39.get_age(self.today_date), 39)

    def test_user_is_0(self):
        """
        Given a profile
        When the profile is born in 19/09/1985 and the date is 28/03/2025
        Then 0 is calculated
        """
        self.user_0 = User.objects.create(username="user_0")
        self.profile_0 = UserProfile.objects.get(user=self.user_0)
        self.profile_0.birth_date=date(2025, 3, 28)
        self.assertEqual(self.profile_0.get_age(self.today_date), 0)

    def test_user_has_no_age(self):
        """
        Given a profile
        When the profile is born in 19/09/1985 and the date is 28/03/2025
        Then 0 is calculated
        """
        self.assertEqual(self.profile.get_age(self.today_date), None)


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

    def test_join_event_creates_checkout(self):
        """
        Given an event
        When a user asks to join it
        Then a checkout form is generated
        """
        fixed_params = {"params": "fixed_params"}
        message = "je veux participer"
        self.event.get_stripe_session_params = MagicMock(return_value=fixed_params)
        mock_session = MagicMock()
        mock_session.url = "www.test.fr"
        with patch('stripe.checkout.Session.create') as mock_stripe_create:
            self.event.get_checkout_page(self.participant, message)
            mock_stripe_create.return_value = mock_session
            mock_stripe_create.assert_called_once_with(
                **fixed_params, 
                metadata={
                    'user_id': self.participant.id,
                    'event_id': self.event.id,
                    'message': message,
                }
            )
            checkout_url = self.event.get_checkout_page(self.participant, message)
            self.assertEqual(checkout_url, "www.test.fr")

    @patch('events.models.Participation.notify_user')
    def test_should_complete_checkout_creates_pending_if_required_capture(self, mock_notify_user):
        with patch.object(self.event, 'notify_organizer') as mock_notify_organizer:
            webhook_message = "je veux participer"
            payment_intent_id = "abc123"
            user_id = self.participant.id
            requires_capture = True
            self.event.create_pending_participation(
                webhook_message,
                payment_intent_id,
                user_id,
                requires_capture,
            )
            participation = Participation.objects.get(user=self.participant, event=self.event)
            mock_notify_user.assert_called_once_with(action="pending")
            mock_notify_organizer.assert_called_once()
            self.assertEqual(participation.message, webhook_message)
            self.assertEqual(participation.stripe_payment_intent, payment_intent_id)
            self.assertEqual(participation.status, Participation.PENDING)


    def test_complete_checkout_should_not_create_pending_if_not_required_capture(self):
        """
        Given an event and a user
        When the user completed a checkout but is no "required_capture"
        Then he's not added to the pending list
        """
        # assert that participation has the right info, simulate right payment intent
        webhook_message = "je veux participer"
        payment_intent_id = "abc123"
        user_id = self.participant.id 
        event_id = self.event.id
        requires_capture=False
        self.event.create_pending_participation(
            webhook_message,
            payment_intent_id,
            self.participant.id, 
            requires_capture,
        )
        self.assertFalse(
            Participation.objects.filter(
                user=self.participant, 
                event=self.event, 
            ).exists()
        )

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
            contact="Test Contact",
        )
        self.participation = Participation.objects.create(
            event=self.event,
            user=self.participant,
            stripe_payment_intent="pi_test_123"
        )

    @patch('stripe.PaymentIntent.capture')
    @patch.object(Participation, 'notify_user')
    def test_should_handle_successful_accept(self, mock_notify_user, mock_capture):
        """
        Given a participation with a valid stripe payment intent,
        When the organizer handles the request with action 'accept',
        Then the payment is captured, user is notified, and status becomes 'accepted'.
        """
        self.participation.handle_request(action='accept', current_user=self.organizer)
        mock_capture.assert_called_once_with("pi_test_123")
        mock_notify_user.assert_called_once_with(action='accept')
        self.assertEqual(self.participation.status, Participation.ACCEPTED)

    @patch.object(Participation, 'notify_user')
    @patch('stripe.PaymentIntent.capture', side_effect=stripe.error.StripeError("Capture failed"))
    def test_should_not_accept_when_stripe_capture_fails(self, mock_capture, mock_notify_user):
        """
        Given a participation with a Stripe intent,
        When Stripe.capture fails,
        Then the status remains unchanged and no notification is sent.
        """
        with self.assertRaises(RuntimeError) as context:
            self.participation.handle_request(action='accept', current_user=self.organizer)
        self.assertIn("Stripe error while processing accept", str(context.exception))
        mock_notify_user.assert_not_called()
        self.assertEqual(self.participation.status, Participation.PENDING)

    def test_should_not_handle_request_with_permission_denied(self):
        """
        Given a user who is not the event organizer,
        When they try to accept a participant,
        Then a PermissionError is raised and nothing happens.
        """
        self.participation.event.can_manage = MagicMock(return_value=False)
        for action in ["accept", "reject"]:
            with self.subTest(action=action):
                with self.assertRaises(PermissionError) as context:
                    self.participation.handle_request(action=action, current_user=self.organizer)
                self.assertIn("can't manage", str(context.exception).lower())
        self.assertEqual(self.participation.status, Participation.PENDING)

    @patch('stripe.PaymentIntent.cancel')
    @patch.object(Participation, 'notify_user')
    def test_should_handle_reject_success(self, mock_notify_user, mock_cancel):
        """
        Given a valid participation with payment intent,
        When the organizer rejects it,
        Then the payment is cancelled, user is notified, and status is 'rejected'.
        """
        self.participation.handle_request(action='reject', current_user=self.organizer)
        mock_cancel.assert_called_once_with("pi_test_123")
        mock_notify_user.assert_called_once_with(action='reject')
        self.assertEqual(self.participation.status, Participation.REJECTED)

    @patch.object(Participation, 'notify_user')
    @patch('stripe.PaymentIntent.cancel', side_effect=stripe.error.StripeError("Cancel failed"))
    def test_handle_reject_stripe_cancel_fails(self, mock_cancel, mock_notify_user):
        """
        Given a participation with a payment intent,
        When Stripe cancel fails during rejection,
        Then a RuntimeError is raised, and status is unchanged.
        """
        with self.assertRaises(RuntimeError) as context:
            self.participation.handle_request(action='reject', current_user=self.organizer)

        self.assertIn("stripe error while processing reject", str(context.exception).lower())

        # Notification ne doit pas être appelée
        mock_notify_user.assert_not_called()

        # Statut doit rester PENDING
        self.participation.refresh_from_db()
        self.assertEqual(self.participation.status, Participation.PENDING)

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
    def test_notify_new_participant(self, mock_send_mail):
        """
        Given a user and an event
        When a new participation is created
        Then the user is notified of his pending status
        """
        self.participation.notify_user(action='pending')
        args, kwargs = mock_send_mail.call_args
        self.assertIn("You will receive all the needed info", args[0])  # message
        self.assertEqual(args[1], settings.DEFAULT_FROM_EMAIL) # source
        self.assertEqual(args[2], [self.participant.email]) # recipient
        notification = Notification.objects.filter(user=self.participant, event=self.event, is_read=False).first()
        self.assertIsNotNone(notification)
        self.assertIn("reviewed", notification.message)

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
        mail_body, _ = mock_send_mail.call_args
        notification = Notification.objects.filter(user=self.participant, event=self.event, is_read=False).first()
        self.assertIsNotNone(notification)
        self.assertIn("accepted", notification.message)
        self.assertIn("Test Contact", mail_body[1])
        self.assertIn("123 Test Street", mail_body[1])



