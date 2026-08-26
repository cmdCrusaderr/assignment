import os

from pydub import AudioSegment
from pydub.utils import mediainfo

KNOWN_EXTS = {".webm", ".ogg", ".wav", ".mp3", ".m4a", ".aac", ".flac"}
CONTENT_TYPE_EXT_MAP = {
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/aac": ".aac",
}


def infer_extension(file_storage):
    _, ext = os.path.splitext(file_storage.filename or "")
    if ext.lower() in KNOWN_EXTS:
        return ext.lower()
    return CONTENT_TYPE_EXT_MAP.get(file_storage.mimetype, ".bin")


def estimate_quality(loudness_dbfs):
    # Rough noise/quality bucket from average loudness.
    # -18 to -3 dBFS: healthy recording level -> good.
    # -30 to -18 dBFS: quiet but usable -> fair.
    # above -3 (near/over 0) or below -30 (or silence): clipping / noise-floor-dominated -> poor.
    if loudness_dbfs is None:
        return "poor", None
    if loudness_dbfs > -3:
        label = "poor"
    elif loudness_dbfs > -18:
        label = "good"
    elif loudness_dbfs > -30:
        label = "fair"
    else:
        label = "poor"
    return label, round(loudness_dbfs, 2)


def extract_audio_metadata(path):
    file_size_bytes = os.path.getsize(path)
    seg = AudioSegment.from_file(path)

    duration_sec = len(seg) / 1000.0
    sample_rate_hz = seg.frame_rate

    dbfs = seg.dBFS
    loudness_dbfs = None if dbfs == float("-inf") else round(dbfs, 2)

    bitrate_kbps = None
    info = mediainfo(path)
    raw_bitrate = info.get("bit_rate")
    if raw_bitrate and str(raw_bitrate).isdigit():
        bitrate_kbps = round(int(raw_bitrate) / 1000.0, 1)
    if not bitrate_kbps and duration_sec > 0:
        bitrate_kbps = round((file_size_bytes * 8) / duration_sec / 1000.0, 1)

    quality_estimate, quality_score = estimate_quality(loudness_dbfs)

    return {
        "duration_sec": round(duration_sec, 2),
        "sample_rate_hz": sample_rate_hz,
        "bitrate_kbps": bitrate_kbps,
        "loudness_dbfs": loudness_dbfs,
        "quality_estimate": quality_estimate,
        "quality_score": quality_score,
        "file_size_bytes": file_size_bytes,
    }


def transcode_to_wav(src_path, dst_path):
    # Browsers disagree on what MediaRecorder actually produces (Chrome:
    # webm/opus, Safari: mp4/aac, ...) and mislabeling is easy to get wrong
    # client-side. Re-encoding everything to one canonical format server-side
    # guarantees the bytes we serve always match the extension/Content-Type,
    # so <audio> playback works regardless of what the browser recorded.
    seg = AudioSegment.from_file(src_path)
    seg.export(dst_path, format="wav")
