import base64

from django.core.files.base import ContentFile
from rest_framework import serializers


class Base64ImageField(serializers.ImageField):
    """Custom ImageField that encode/decode image data to a string."""
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format_type, image_string = data.split(';base64,')
            ext = format_type.split('/')[-1]
            data = ContentFile(
                base64.b64decode(image_string), name='temp.' + ext
            )
        return super().to_internal_value(data)
