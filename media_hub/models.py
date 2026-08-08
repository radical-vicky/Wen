from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from cloudinary.models import CloudinaryField


class Media(models.Model):
    VIDEO = 'video'
    IMAGE = 'image'
    AUDIO = 'audio'
    MEDIA_TYPE_CHOICES = [
        (VIDEO, 'Video'),
        (IMAGE, 'Image'),
        (AUDIO, 'Song'),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='media_items')
    media_type = models.CharField(max_length=5, choices=MEDIA_TYPE_CHOICES)
    title = models.CharField(max_length=120)
    caption = models.CharField(max_length=280, blank=True)

    # Cloudinary handles images, videos and audio; resource_type differs per
    # instance, so we store it as 'auto' and let Cloudinary detect the type
    # on upload. Cloudinary stores audio under its 'video' resource type
    # internally, which 'auto' handles transparently.
    file = CloudinaryField(
        'media',
        folder='uploads',
        resource_type='auto',
    )
    # Optional cover art for songs (falls back to a generic icon in the UI).
    cover = CloudinaryField(
        'cover',
        folder='covers',
        resource_type='image',
        blank=True,
        null=True,
    )

    views_count = models.PositiveIntegerField(default=0)
    downloads_count = models.PositiveIntegerField(default=0)
    shares_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.media_type})"

    def get_absolute_url(self):
        return reverse('media_hub:detail', kwargs={'pk': self.pk})

    @property
    def is_video(self):
        return self.media_type == self.VIDEO

    @property
    def is_image(self):
        return self.media_type == self.IMAGE

    @property
    def is_audio(self):
        return self.media_type == self.AUDIO

    @property
    def likes_count(self):
        return self.likes.count()

    @property
    def comments_count(self):
        return self.comments.count()

    def is_liked_by(self, user):
        if not user or not user.is_authenticated:
            return False
        return self.likes.filter(user=user).exists()


class Like(models.Model):
    media = models.ForeignKey(Media, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('media', 'user')

    def __str__(self):
        return f"{self.user} likes {self.media}"


class Comment(models.Model):
    media = models.ForeignKey(Media, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    body = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} on {self.media}: {self.body[:30]}"
