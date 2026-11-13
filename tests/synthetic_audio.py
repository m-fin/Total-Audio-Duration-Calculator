"""Tiny synthetic audio files for tests.

These are generated at runtime and are not committed. They contain no
recorded or copyrighted audio. WAV files are silent PCM. The other files are
minimal headers that mutagen can time without a real encoded payload.
"""

import struct
import wave


# MPEG-1 Layer III, 128 kbps, 44100 Hz, no padding.
# Frame length = (144 * 128000) // 44100 = 417 bytes.
MP3_FRAME_BYTES = 417
MP3_BITRATE = 128_000
MP3_FRAMES_FOR_ABOUT_ONE_SECOND = 38


def mp3_duration_seconds(frames=MP3_FRAMES_FOR_ABOUT_ONE_SECOND):
    """Duration mutagen reports for a CBR file of this many frames.

    With no Xing header, mutagen estimates ``8 * file_size / bitrate``.
    """
    return 8 * frames * MP3_FRAME_BYTES / MP3_BITRATE


def write_wav(path, seconds, sample_rate=8000):
    """Write silent 16-bit mono PCM of exactly ``seconds`` (sample-aligned)."""
    frame_count = int(round(seconds * sample_rate))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\x00\x00" * frame_count)


def write_flac(path, seconds, sample_rate=44100):
    """Write a FLAC stream whose STREAMINFO duration is ``seconds``."""
    total_samples = int(round(seconds * sample_rate))
    channels = 1
    bits_per_sample = 16
    # 20-bit rate, 3-bit channel count, 5-bit sample width, 36-bit sample count.
    packed = (
        (sample_rate & 0xFFFFF) << 44
        | ((channels - 1) & 0x7) << 41
        | ((bits_per_sample - 1) & 0x1F) << 36
        | (total_samples & 0xFFFFFFFFF)
    )
    streaminfo = (
        struct.pack(">HH", 16, 16)
        + b"\x00" * 6
        + struct.pack(">Q", packed)
        + b"\x00" * 16
    )
    if len(streaminfo) != 34:
        raise RuntimeError(f"STREAMINFO must be 34 bytes, got {len(streaminfo)}")
    # Last-metadata-block flag set, block type 0 (STREAMINFO).
    block_header = bytes([0x80]) + struct.pack(">I", 34)[1:]
    path.write_bytes(b"fLaC" + block_header + streaminfo)


def write_mp4(path, seconds, timescale=1000):
    """Write an MPEG-4 container whose movie header lasts ``seconds``.

    The same bytes are valid stand-ins for .m4a, .m4b, and .mp4 audio.
    """
    duration = int(round(seconds * timescale))
    ftyp = struct.pack(">I4s4sI4s", 20, b"ftyp", b"mp42", 0, b"isom")
    mvhd = (
        struct.pack(">I", 0)  # version 0, flags 0
        + struct.pack(">II", 0, 0)  # creation, modification
        + struct.pack(">II", timescale, duration)
        + b"\x00" * 80
    )
    path.write_bytes(ftyp + _box(b"moov", _box(b"mvhd", mvhd)))


def write_ogg(path, seconds, sample_rate=44100):
    """Write an Ogg Vorbis bitstream whose granule position is ``seconds``."""
    from mutagen.ogg import OggPage

    channels = 1
    ident = b"\x01vorbis" + struct.pack(
        "<IBIiiiBB", 0, channels, sample_rate, 0, 128000, 0, 0xBB, 1
    )
    vendor = b"synthetic"
    comment = (
        b"\x03vorbis"
        + struct.pack("<I", len(vendor))
        + vendor
        + struct.pack("<I", 0)
        + b"\x01"
    )
    granule = int(round(seconds * sample_rate))
    pages = [
        (0, ident, True, False, 0),
        (1, comment, False, False, 0),
        (2, b"\x00", False, True, granule),
    ]
    blob = bytearray()
    for sequence, packet, first, last, position in pages:
        page = OggPage()
        page.serial = 1
        page.sequence = sequence
        page.packets = [packet]
        page.first = first
        page.last = last
        page.position = position
        blob.extend(page.write())
    path.write_bytes(blob)


def write_mp3(path, frames=MP3_FRAMES_FOR_ABOUT_ONE_SECOND):
    """Write CBR MPEG frames. Returns the duration mutagen will report."""
    # 0xFFFB: MPEG-1, Layer III, no CRC. 0x90: 128 kbps, 44100 Hz, no padding.
    header = bytes((0xFF, 0xFB, 0x90, 0x00))
    frame = header + bytes(MP3_FRAME_BYTES - len(header))
    path.write_bytes(frame * frames)
    return mp3_duration_seconds(frames)


def _box(name, payload):
    return struct.pack(">I4s", 8 + len(payload), name) + payload
