import io
import subprocess
import tempfile
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from PIL import Image, ImageOps


def _is_image(content_type: str) -> bool:
    return bool(content_type and content_type.startswith("image/"))


def _is_video(content_type: str) -> bool:
    return bool(content_type and content_type.startswith("video/"))


def optimize_image(uploaded_file, quality: int = 78, max_size: int = 1920):
    if not _is_image(getattr(uploaded_file, "content_type", "")):
        return uploaded_file

    uploaded_file.seek(0)
    img = Image.open(uploaded_file)
    img = ImageOps.exif_transpose(img)

    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    elif img.mode == "L":
        img = img.convert("RGB")

    img.thumbnail((max_size, max_size))

    out = io.BytesIO()
    img.save(out, format="JPEG", optimize=True, quality=quality, progressive=True)
    out.seek(0)

    return InMemoryUploadedFile(
        out,
        field_name=getattr(uploaded_file, "field_name", "file"),
        name=f"{Path(getattr(uploaded_file, 'name', 'image')).stem}.jpg",
        content_type="image/jpeg",
        size=out.getbuffer().nbytes,
        charset=None,
    )


def optimize_video(uploaded_file, crf: int = 28, preset: str = "veryfast"):
    if not _is_video(getattr(uploaded_file, "content_type", "")):
        return uploaded_file

    with tempfile.TemporaryDirectory() as tmp:
        in_path = Path(tmp) / "input"
        out_path = Path(tmp) / "output.mp4"

        if isinstance(uploaded_file, TemporaryUploadedFile):
            in_path = Path(uploaded_file.temporary_file_path())
        else:
            uploaded_file.seek(0)
            with in_path.open("wb") as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(in_path),
            "-vcodec",
            "libx264",
            "-crf",
            str(crf),
            "-preset",
            preset,
            "-acodec",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(out_path),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return uploaded_file

        out_bytes = out_path.read_bytes()
        return ContentFile(out_bytes, name=f"{Path(getattr(uploaded_file, 'name', 'video')).stem}.mp4")


def optimize_media(uploaded_file):
    content_type = getattr(uploaded_file, "content_type", "") or ""
    if _is_image(content_type):
        return optimize_image(uploaded_file)
    if _is_video(content_type):
        return optimize_video(uploaded_file)
    return uploaded_file
