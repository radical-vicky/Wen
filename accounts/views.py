from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.paginator import Paginator

from .forms import ProfileForm
from media_hub.models import Media


def profile_view(request, username):
    profile_user = get_object_or_404(User, username=username)
    media_qs = Media.objects.filter(owner=profile_user).order_by('-created_at')
    paginator = Paginator(media_qs, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'accounts/profile.html', {
        'profile_user': profile_user,
        'page_obj': page_obj,
        'is_own_profile': request.user.is_authenticated and request.user == profile_user,
    })


@login_required
def edit_profile(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect('accounts:profile', username=request.user.username)
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'accounts/edit_profile.html', {'form': form})
