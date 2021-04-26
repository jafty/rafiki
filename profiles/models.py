from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.forms import ModelForm


class UserProfile(models.Model):
	profile_pic = models.ImageField(upload_to="profiles", default="/media/defaultpp.jpg")
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
	age = models.IntegerField(blank=True)
	bio = models.TextField()
	parties_att_nb = models.IntegerField(default=0)
	parties_org_nb = models.IntegerField(default=0)
	is_organizer = models.BooleanField(default=False)

	def __str__(self):
		return self.user.username


class UserProfileForm(ModelForm):
	class Meta:
		model = UserProfile
		fields = (
			"profile_pic",
			"age",
			"bio",
			)

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
	if created:        
		UserProfile.objects.get_or_create(user=instance)
	instance.profile.save()
