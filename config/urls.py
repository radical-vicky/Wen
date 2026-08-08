from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),   # login, signup, logout, Google OAuth
    path('u/', include('accounts.urls')),           # profile pages
    path('', include('media_hub.urls')),
]
