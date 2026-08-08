"""
Best-effort enrichment of a Profile when a user signs up via a social
provider (currently just Google): pull their display name and avatar
across so the profile isn't empty on first visit. Never blocks signup —
any failure here is logged and swallowed.
"""
import logging

from django.dispatch import receiver
from allauth.socialaccount.signals import social_account_added

logger = logging.getLogger(__name__)


@receiver(social_account_added)
def populate_profile_from_social_account(request, sociallogin, **kwargs):
    try:
        account = sociallogin.account
        if account.provider != 'google':
            return

        profile = sociallogin.user.profile
        extra = account.extra_data or {}
        changed = False

        if not profile.display_name and extra.get('name'):
            profile.display_name = extra['name'][:80]
            changed = True

        picture_url = extra.get('picture')
        if picture_url and not profile.avatar:
            import cloudinary.uploader
            upload_result = cloudinary.uploader.upload(picture_url, folder='avatars')
            profile.avatar = upload_result.get('public_id')
            changed = True

        if changed:
            profile.save()
    except Exception:
        logger.exception("Could not enrich profile from Google account data")
