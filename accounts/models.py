from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from cloudinary.models import CloudinaryField


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    display_name = models.CharField(max_length=80, blank=True)
    bio = models.CharField(max_length=200, blank=True)
    avatar = CloudinaryField(
        'avatar',
        folder='avatars',
        blank=True,
        null=True,
        resource_type='image',
    )
    website = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username

    def get_absolute_url(self):
        return reverse('accounts:profile', kwargs={'username': self.user.username})

    @property
    def name_or_username(self):
        return self.display_name or self.user.username


# Auto-create a Profile whenever a User is created.
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=User)
def create_or_save_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        Profile.objects.get_or_create(user=instance)
