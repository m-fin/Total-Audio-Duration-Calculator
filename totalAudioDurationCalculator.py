#!/usr/bin/env python3
"""Total the duration of audio files in a directory.

Examples:
    python totalAudioDurationCalculator.py /path/to/album
    python totalAudioDurationCalculator.py /path/to/album -e mp3,flac,m4a
"""

import argparse
import datetime
import math
import os
import re
import sys

from mutagen import File as MutagenFile


# Used when --extensions is omitted. Matching is case-insensitive.
DEFAULT_EXTENSIONS = (
    "mp3",
    "flac",
    "m4a",
    "m4b",
    "mp4",
    "wav",
    "ogg",
    "oga",
    "opus",
    "aac",
    "aiff",
    "aif",
    "wma",
    "wv",
    "ape",
)

_EXTENSION_SPLIT = re.compile(r"[\s,]+")


def parse_extensions(values):
    """Return a unique list of lowercase extensions, without leading dots.

    ``values`` is the list of ``--extensions`` arguments, or None for the
    default set. Each argument may hold several names, separated by commas
    or spaces (``.m4a, FLAC``).
    """
    if not values:
        return list(DEFAULT_EXTENSIONS)

    found = []
    seen = set()
    for value in values:
        for raw in _EXTENSION_SPLIT.split(value.strip()):
            extension = raw.lower().strip(".")
            if not extension:
                continue
            if "/" in extension or "\\" in extension:
                raise ValueError("invalid extension: %s" % raw)
            if extension not in seen:
                seen.add(extension)
                found.append(extension)
    if not found:
        raise ValueError(
            "no extensions given; pass names such as mp3,flac,m4a"
        )
    return found


def format_duration(seconds):
    """Format a duration as ``H:MM:SS``, rounded to the nearest second."""
    return str(datetime.timedelta(seconds=round(seconds)))


def read_duration_seconds(path):
    """Return one file's duration in seconds.

    Raises ValueError when the file is not readable audio.
    """
    # A single unreadable file must not abort the total for the directory.
    try:
        audio = MutagenFile(path)
    except Exception as exc:
        raise ValueError(_error_text(exc)) from exc

    info = getattr(audio, "info", None) if audio is not None else None
    length = getattr(info, "length", None)
    if length is None:
        raise ValueError("unrecognized audio format")
    try:
        seconds = float(length)
    except (TypeError, ValueError) as exc:
        raise ValueError("duration is unavailable") from exc
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError("duration is unavailable")
    return seconds


def scan_directory(directory, extensions):
    """Sum matching files that sit directly in ``directory``.

    Returns ``(total_seconds, skipped)``. ``skipped`` is a list of
    ``(filename, reason)`` in filename order. Subdirectories are ignored.
    """
    wanted = {extension.lower().lstrip(".") for extension in extensions}

    entries = list(os.scandir(directory))

    total = 0.0
    skipped = []
    for entry in sorted(entries, key=lambda item: item.name):
        try:
            is_file = entry.is_file()
        except OSError:
            continue
        if not is_file:
            continue
        extension = os.path.splitext(entry.name)[1].lstrip(".").lower()
        if extension not in wanted:
            continue
        try:
            total += read_duration_seconds(entry.path)
        except ValueError as exc:
            skipped.append((entry.name, str(exc)))
    return total, skipped


def getTotalAudioDuration(path, extensions=None):
    """Return the total duration of audio in ``path`` as ``H:MM:SS``.

    Files that match ``extensions`` but cannot be read are reported on
    stderr and left out of the total. ``extensions`` defaults to
    ``DEFAULT_EXTENSIONS``. A comma-separated string is accepted as well
    as a list of names.
    """
    if isinstance(extensions, str):
        extensions = [extensions]
    chosen = parse_extensions(extensions)
    total, skipped = scan_directory(path, chosen)
    _report_skipped(skipped)
    return format_duration(total)


def _error_text(exc):
    text = str(exc).strip()
    return text or "could not read audio file"


def _report_skipped(skipped):
    for name, reason in skipped:
        print("Skipping %s: %s" % (name, reason), file=sys.stderr)


def build_parser():
    default_list = ",".join(DEFAULT_EXTENSIONS)
    parser = argparse.ArgumentParser(
        prog="totalAudioDurationCalculator.py",
        description="Total the duration of audio files in a directory.",
        epilog=(
            "Examples:\n"
            "  python totalAudioDurationCalculator.py /path/to/album\n"
            "  python totalAudioDurationCalculator.py /path/to/album -e mp3,flac,m4a\n"
            "\n"
            "Default extensions: %s" % default_list
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "directory",
        help="Directory containing the audio files",
    )
    parser.add_argument(
        "-e",
        "--extensions",
        action="append",
        metavar="EXT",
        help=(
            "Extensions to include, separated by commas or spaces "
            "(mp3,flac or .m4a). Repeat the flag to add more. "
            "Matching is case-insensitive. "
            "Defaults to the common types listed below."
        ),
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        extensions = parse_extensions(args.extensions)
    except ValueError as exc:
        parser.error(str(exc))

    directory = args.directory
    if not os.path.exists(directory):
        print("No such directory: %s" % directory, file=sys.stderr)
        return 1
    if not os.path.isdir(directory):
        print("Not a directory: %s" % directory, file=sys.stderr)
        return 1

    try:
        duration = getTotalAudioDuration(directory, extensions)
    except OSError as exc:
        detail = exc.strerror or str(exc)
        print(
            "Cannot read directory: %s (%s)" % (directory, detail),
            file=sys.stderr,
        )
        return 1

    print("Total duration:")
    print(duration)
    return 0


if __name__ == "__main__":
    sys.exit(main())
