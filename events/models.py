from django.db import models
from django.utils import timezone
from django.db.models import Q
from django.shortcuts import render
from django.contrib.auth.models import User
from datetime import datetime, date, timedelta
from django.core.validators import MaxValueValidator, MinValueValidator


class Event(models.Model):
	"""
	Handles the events informations
	"""
	author = models.ForeignKey("auth.user", on_delete="CASCADE")
	name = models.CharField(max_length=30)
	description = models.TextField(default="")
	date = models.DateField(default=datetime.now)
	hour = models.TimeField(default=datetime.now)
	price = models.IntegerField(default=0)
	picture = models.ImageField(upload_to="events", max_length=100, default="/media/default.jpg")
	address = models.CharField(max_length=500, default="")
	hidden = models.BooleanField(default=False)

	@property
	def is_past(self):
		return (date.today()+timedelta(hours=6)) > self.date

	def __str__(self):
		return self.name


class Notification(models.Model):
	"""
	Handle the messages sent to users, they might be sent from the system,
	or by another user if this feature comes in 
	"""
	sender = models.ForeignKey(User, related_name="sender", on_delete="CASCADE")
	receiver = models.ForeignKey(User, related_name="receiver", on_delete="CASCADE")
	event = models.ForeignKey(Event, related_name="msg_event", on_delete="CASCADE")
	msg_content = models.TextField()
	type = models.CharField(max_length=5)

	def __str__(self):
		return self.sender.username


class ParticipationList(models.Model):
	"""
	This class is used to store participations of users to events
	"""
	member = models.ForeignKey(User, related_name="member", on_delete="CASCADE")
	event = models.ForeignKey(Event, related_name="list_event", on_delete="CASCADE")

	def __str__(self):
		return self.member.username + " " + self.event.name

