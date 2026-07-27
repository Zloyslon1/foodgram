import base64

from django.core.files.base import ContentFile
from rest_framework import serializers

FORMAT_ERROR = 'Некорректный формат изображения.'


class Base64ImageField(serializers.ImageField):
    """Картинка в формате data:image/...;base64,..."""

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            header, separator, encoded = data.partition(';base64,')
            if not separator:
                raise serializers.ValidationError(FORMAT_ERROR)
            extension = header.split('/')[-1]
            try:
                decoded = base64.b64decode(encoded)
            except ValueError:
                raise serializers.ValidationError(FORMAT_ERROR)
            data = ContentFile(decoded, name=f'image.{extension}')
        return super().to_internal_value(data)
