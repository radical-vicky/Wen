from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('me/edit/', views.edit_profile, name='edit_profile'),
    path('<str:username>/', views.profile_view, name='profile'),
]
