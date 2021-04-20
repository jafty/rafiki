from django.db import models
from django.utils import timezone
from django.db.models import Q
from django.shortcuts import render
from django.contrib.auth.models import User
from datetime import datetime, date, timedelta
from django.core.validators import MaxValueValidator, MinValueValidator

# Create your models here.

# This is a test edit

class Event(models.Model):
	author = models.ForeignKey("auth.user", on_delete="CASCADE")
	name = models.CharField(max_length=30)
	date = models.DateField(default=datetime.now)
	hour = models.TimeField(default=datetime.now)
	price = models.IntegerField(default=0)

	@property
	def is_past(self):
		return (date.today()+timedelta(hours=6)) > self.date

	def __str__(self):
		return self.name


class Notification(models.Model):
	sender = models.ForeignKey(User, related_name="sender", on_delete="CASCADE")
	receiver = models.ForeignKey(User, related_name="receiver", on_delete="CASCADE")
	event = models.ForeignKey(Event, related_name="msg_event", on_delete="CASCADE")
	msg_content = models.TextField()
	type = models.CharField(max_length=5)

	def __str__(self):
		return self.sender.username

