"""Upload handling shared by the profile, projects and image library: size checks, resizing, cleanup of
replaced files."""

from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 40_000_000  # about 6300 × 6300, so a small file can't decompress into a giant image


def validate_upload_size(file):
    if file.size > MAX_UPLOAD_BYTES:
        raise ValidationError('The file must be 5 MB or smaller.')


def validate_pdf(file):
    validate_upload_size(file)
    head = file.read(5)
    file.seek(0)
    if not file.name.lower().endswith('.pdf') or head != b'%PDF-':
        raise ValidationError('Upload a PDF file.')


def validate_image(file):
    """A real PNG, JPEG, WebP or GIF within the size and pixel limits."""
    validate_upload_size(file)
    try:
        with Image.open(file) as image:
            if image.format not in ('PNG', 'JPEG', 'WEBP', 'GIF'):
                raise ValidationError('Upload a PNG, JPEG, WebP or GIF image.')
            width, height = image.size
            image.verify()
    except ValidationError:
        raise
    except Exception:  # Pillow raises several error types for broken or disguised files
        raise ValidationError('This file is not a readable image.')
    finally:
        file.seek(0)
    if width * height > MAX_PIXELS:
        raise ValidationError(f'The image is {width} × {height} pixels; the limit is about 40 million pixels.')


def to_webp(upload, max_side):
    """Re-encode as WebP, scaled down to fit max_side. Re-encoding keeps only the pixels, so camera and location
    data and anything else hidden in the file are dropped. Returns (file, (width, height))."""
    image = _open(upload)
    transparent = 'A' in image.getbands() or 'transparency' in image.info
    image = image.convert('RGBA' if transparent else 'RGB')
    image.thumbnail((max_side, max_side), Image.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, format='WEBP', quality=82, method=6)
    return ContentFile(buffer.getvalue()), image.size


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
