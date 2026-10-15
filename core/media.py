"""Upload handling shared by the profile and projects: size checks, resizing, cleanup of replaced files."""

from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def validate_upload_size(file):
    if file.size > MAX_UPLOAD_BYTES:
        raise ValidationError('The file must be 5 MB or smaller.')


def validate_pdf(file):
    validate_upload_size(file)
    head = file.read(5)
    file.seek(0)
    if not file.name.lower().endswith('.pdf') or head != b'%PDF-':
        raise ValidationError('Upload a PDF file.')


def _open(upload):
    return ImageOps.exif_transpose(Image.open(upload))


def _save(image, fmt):
    buffer = BytesIO()
    if fmt == 'JPEG':
        image.convert('RGB').save(buffer, format='JPEG', quality=85, optimize=True, progressive=True)
    else:
        image.save(buffer, format='PNG', optimize=True)
    return ContentFile(buffer.getvalue())


def fit_image(upload, size, fmt='PNG'):
    """Centre-crop to the size's aspect ratio and resize to exactly that size."""
    image = _open(upload).convert('RGBA' if fmt == 'PNG' else 'RGB')
    return _save(ImageOps.fit(image, size, Image.LANCZOS), fmt)


def shrink_image(upload, max_width, fmt='PNG'):
    """Keep the aspect ratio; only scale down when wider than max_width."""
    image = _open(upload).convert('RGBA' if fmt == 'PNG' else 'RGB')
    if image.width > max_width:
        image = image.resize((max_width, round(image.height * max_width / image.width)), Image.LANCZOS)
    return _save(image, fmt)


def previous_files(model, pk, fields):
    """Stored file names before a save, so replaced or cleared files can be deleted afterwards."""
    if pk is None:
        return {}
    return model.objects.filter(pk=pk).values(*fields).first() or {}


def delete_replaced(instance, previous):
    for field, old in previous.items():
        if old and old != getattr(instance, field).name:
            getattr(instance, field).storage.delete(old)
