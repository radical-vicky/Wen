from django.urls import path
from . import views

app_name = 'media_hub'

urlpatterns = [
    path('', views.feed, name='feed'),
    path('reels/', views.reels, name='reels'),
    path('upload/', views.upload, name='upload'),
    path('upload/finalize/', views.finalize_upload, name='finalize_upload'),
    path('m/<int:pk>/', views.detail, name='detail'),
    path('m/<int:pk>/json/', views.track_json, name='track_json'),
    path('m/<int:pk>/delete/', views.delete_media, name='delete'),
    path('m/<int:pk>/like/', views.toggle_like, name='toggle_like'),
    path('m/<int:pk>/comment/', views.add_comment, name='add_comment'),
    path('m/<int:pk>/comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),
    path('m/<int:pk>/share/', views.register_share, name='register_share'),
    path('m/<int:pk>/download/', views.download, name='download'),
]
