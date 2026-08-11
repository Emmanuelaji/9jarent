import os
import tempfile
import ffmpeg
from django.core.exceptions import ValidationError

def validate_video_file(video_file):
    if video_file.size > 3 * 1024 * 1024:
        raise ValidationError("Video must be less than 3MB.")
    ext = os.path.splitext(video_file.name)[1].lower()
    if ext != '.mp4':
        raise ValidationError("Only MP4 format is allowed.")

    # Freshly uploaded files may be held in memory (no real .path yet) rather
    # than on disk, so write to a temp file to guarantee ffprobe can read it.
    tmp_path = None
    try:
        if hasattr(video_file, 'temporary_file_path'):
            probe_path = video_file.temporary_file_path()
        else:
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
                for chunk in video_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
            probe_path = tmp_path
            video_file.seek(0)

        probe = ffmpeg.probe(probe_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        if not video_stream:
            raise ValidationError("No video stream found in file.")
        width = int(video_stream.get('width', 0))
        height = int(video_stream.get('height', 0))
        if width < 1280 or height < 720:
            raise ValidationError("Video must be HD quality (720p or higher).")
        if video_stream.get('codec_name') != 'h264':
            raise ValidationError("Video must use H.264 codec.")
    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f"Invalid video file: {str(e)}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

def validate_image_file(image_file):
    if image_file.size > 5 * 1024 * 1024:
        raise ValidationError("Image must be less than 5MB.")
    ext = os.path.splitext(image_file.name)[1].lower()
    if ext not in ['.jpg', '.jpeg', '.png']:
        raise ValidationError("Only JPEG and PNG formats are allowed.")
