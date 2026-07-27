"""
File: app/infrastructure/media/profile_photo.py
Folder: backend/app/infrastructure/media
Purpose: Turn an uploaded avatar image into a small, storage-ready data URI.
         Profile photos are a single small image per user (unlike TISAX
         evidence documents, which can be many large files per control), so
         storing them as base64 directly on the user row is simplest: no
         extra storage key, no separate "serve image" endpoint with its own
         content-type/caching concerns — the photo just travels inside
         UserResponse and the browser renders it directly.

         Images are resized down to a small square thumbnail and re-encoded
         as JPEG, keeping the stored payload small regardless of what the
         user uploads.
"""

import base64
from io import BytesIO

from app.core.exceptions import ValidationError

ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5MB raw upload cap, before resizing
MAX_DIMENSION = 256  # px, thumbnail size stored


def process_profile_photo(content: bytes, mime_type: str) -> str:
    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValidationError("Profile photo must be a PNG, JPEG, or WEBP image.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValidationError("Profile photo must be smaller than 5MB.")

    from PIL import Image  # local import: keeps Pillow optional for other callers

    try:
        image = Image.open(BytesIO(content))
        image = image.convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise ValidationError("Could not read this image file.") from exc

    image.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"