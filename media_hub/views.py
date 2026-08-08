import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.http import HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

import cloudinary.utils

from .forms import CommentForm
from .models import Comment, Like, Media

_SAFE_TOKEN_RE = re.compile(r'^[A-Za-z0-9_\-./]+$')


def _is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


def feed(request):
    media_type = request.GET.get('type')
    qs = Media.objects.select_related('owner', 'owner__profile').prefetch_related('likes', 'comments')
    if media_type in ('video', 'image', 'audio'):
        qs = qs.filter(media_type=media_type)
    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    hero_items = list(
        Media.objects.filter(media_type__in=['video', 'image'])
        .select_related('owner')
        .order_by('-views_count', '-created_at')[:6]
    )

    return render(request, 'media_hub/feed.html', {
        'page_obj': page_obj,
        'active_filter': media_type or 'all',
        'hero_items': hero_items,
    })


def reels(request):
    """TikTok-style fullscreen, swipeable vertical video feed."""
    videos = list(
        Media.objects.filter(media_type=Media.VIDEO)
        .select_related('owner', 'owner__profile')
        .prefetch_related('likes', 'comments')
        .order_by('-created_at')[:60]
    )
    start_pk = request.GET.get('start')
    if start_pk:
        try:
            start_pk = int(start_pk)
            idx = next((i for i, v in enumerate(videos) if v.pk == start_pk), None)
            if idx:
                videos = videos[idx:] + videos[:idx]
        except (TypeError, ValueError):
            pass
    for v in videos:
        v.viewer_liked = v.is_liked_by(request.user)
    return render(request, 'media_hub/reels.html', {'videos': videos})


def detail(request, pk):
    item = get_object_or_404(
        Media.objects.select_related('owner', 'owner__profile'), pk=pk
    )
    Media.objects.filter(pk=pk).update(views_count=F('views_count') + 1)
    item.refresh_from_db()
    comments = item.comments.select_related('user', 'user__profile')
    comment_form = CommentForm()

    more_from_creator = list(
        Media.objects.filter(owner=item.owner, media_type=item.media_type)
        .exclude(pk=item.pk)
        .select_related('owner')[:8]
    )
    discover_more = list(
        Media.objects.filter(media_type=item.media_type)
        .exclude(pk=item.pk)
        .exclude(owner=item.owner)
        .select_related('owner')
        .order_by('-created_at')[:8]
    )
    up_next_ids = [m.pk for m in more_from_creator] + [m.pk for m in discover_more]

    return render(request, 'media_hub/detail.html', {
        'item': item,
        'comments': comments,
        'comment_form': comment_form,
        'is_liked': item.is_liked_by(request.user),
        'more_from_creator': more_from_creator,
        'discover_more': discover_more,
        'up_next_ids': up_next_ids,
    })


@login_required
def upload(request):
    """Renders the drag & drop uploader. The actual file bytes never touch
    this server — the browser uploads directly to Cloudinary via an
    unsigned preset, then calls finalize_upload with the result."""
    return render(request, 'media_hub/upload.html')


@login_required
@require_POST
def finalize_upload(request):
    """Called by the uploader JS after a file has already landed on
    Cloudinary. We just record the metadata — no file handling here, which
    is what makes this path fast."""
    try:
        payload = __import__('json').loads(request.body.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return HttpResponseBadRequest('Invalid payload')

    title = (payload.get('title') or '').strip()[:120]
    caption = (payload.get('caption') or '').strip()[:280]
    media_type = payload.get('media_type')
    public_id = payload.get('public_id') or ''
    resource_type = payload.get('resource_type') or ''
    fmt = payload.get('format') or ''
    version = payload.get('version') or ''
    cover_public_id = payload.get('cover_public_id') or ''

    if media_type not in (Media.VIDEO, Media.IMAGE, Media.AUDIO):
        return HttpResponseBadRequest('Invalid media type')
    if not title:
        return HttpResponseBadRequest('Title is required')
    for token in (public_id, resource_type, fmt, cover_public_id):
        if token and not _SAFE_TOKEN_RE.match(str(token)):
            return HttpResponseBadRequest('Invalid upload reference')
    if version and not str(version).isdigit():
        return HttpResponseBadRequest('Invalid upload reference')
    if not public_id or resource_type not in ('image', 'video', 'raw'):
        return HttpResponseBadRequest('Missing upload reference')

    file_value = f"{resource_type}/upload/"
    if version:
        file_value += f"v{version}/"
    file_value += public_id
    if fmt:
        file_value += f".{fmt}"

    media = Media(owner=request.user, media_type=media_type, title=title, caption=caption)
    media.file = file_value
    if cover_public_id:
        media.cover = f"image/upload/{cover_public_id}"
    media.save()

    return JsonResponse({'redirect_url': media.get_absolute_url()})


@login_required
def delete_media(request, pk):
    item = get_object_or_404(Media, pk=pk, owner=request.user)
    if request.method == 'POST':
        item.delete()
        messages.success(request, "Deleted.")
        return redirect('accounts:profile', username=request.user.username)
    return render(request, 'media_hub/confirm_delete.html', {'item': item})


@login_required
@require_POST
def toggle_like(request, pk):
    item = get_object_or_404(Media, pk=pk)
    like, created = Like.objects.get_or_create(media=item, user=request.user)
    if not created:
        like.delete()
        liked = False
    else:
        liked = True

    if _is_ajax(request):
        return JsonResponse({'liked': liked, 'likes_count': item.likes_count})
    return redirect(request.META.get('HTTP_REFERER', item.get_absolute_url()))


@login_required
@require_POST
def add_comment(request, pk):
    item = get_object_or_404(Media, pk=pk)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.media = item
        comment.user = request.user
        comment.save()

        if _is_ajax(request):
            html = render_to_string('media_hub/_comment.html', {'comment': comment, 'item': item}, request=request)
            return JsonResponse({'ok': True, 'html': html, 'comments_count': item.comments_count})
        messages.success(request, "Comment posted.")
    else:
        if _is_ajax(request):
            return JsonResponse({'ok': False, 'errors': form.errors}, status=400)
        messages.error(request, "Comment couldn't be posted.")
    return redirect('media_hub:detail', pk=item.pk)


@login_required
@require_POST
def delete_comment(request, pk, comment_id):
    item = get_object_or_404(Media, pk=pk)
    comment = get_object_or_404(Comment, pk=comment_id, media=item)
    if request.user == comment.user or request.user == item.owner:
        comment.delete()
        if _is_ajax(request):
            return JsonResponse({'ok': True, 'comments_count': item.comments_count})
        messages.success(request, "Comment removed.")
    return redirect('media_hub:detail', pk=item.pk)


@require_POST
def register_share(request, pk):
    """Bumped via JS right before the share link is copied/opened."""
    item = get_object_or_404(Media, pk=pk)
    Media.objects.filter(pk=pk).update(shares_count=F('shares_count') + 1)
    return JsonResponse({'shares_count': item.shares_count + 1})


def download(request, pk):
    item = get_object_or_404(Media, pk=pk)
    Media.objects.filter(pk=pk).update(downloads_count=F('downloads_count') + 1)

    resource_type = 'image' if item.is_image else 'video'  # Cloudinary buckets audio under 'video'
    public_id = item.file.public_id
    fmt = getattr(item.file, 'format', None)

    download_url, _ = cloudinary.utils.cloudinary_url(
        public_id,
        resource_type=resource_type,
        format=fmt,
        flags='attachment',
    )
    return HttpResponseRedirect(download_url)


def track_json(request, pk):
    """Small JSON payload the mini-player uses to load a track without a
    full page navigation (used when advancing to the next song)."""
    item = get_object_or_404(Media.objects.select_related('owner'), pk=pk, media_type=Media.AUDIO)
    return JsonResponse({
        'id': item.pk,
        'title': item.title,
        'artist': item.owner.username,
        'src': item.file.url,
        'cover': item.cover.url if item.cover else '',
        'detail_url': item.get_absolute_url(),
    })
