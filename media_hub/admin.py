from django.contrib import admin
from .models import Media, Like, Comment


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'media_type', 'views_count', 'downloads_count', 'shares_count', 'created_at')
    list_filter = ('media_type',)
    search_fields = ('title', 'owner__username')


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('media', 'user', 'created_at')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('media', 'user', 'body', 'created_at')
    search_fields = ('body', 'user__username')
