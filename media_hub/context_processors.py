from django.conf import settings


def cloudinary_settings(request):
    """Expose the public bits Cloudinary's browser-side upload widget needs.
    Only the cloud name and an *unsigned* preset are ever sent to the
    client — never the API secret."""
    cloud_name = settings.CLOUDINARY_STORAGE.get('CLOUD_NAME', '')
    return {
        'CLOUDINARY_CLOUD_NAME': cloud_name,
        'CLOUDINARY_UPLOAD_PRESET': settings.CLOUDINARY_UPLOAD_PRESET,
        'CLOUDINARY_UPLOAD_URL': f'https://api.cloudinary.com/v1_1/{cloud_name}/auto/upload' if cloud_name else '',
    }
