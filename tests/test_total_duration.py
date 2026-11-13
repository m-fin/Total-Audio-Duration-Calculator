"""CLI tests for totaling audio durations across file types."""

import datetime
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from synthetic_audio import (
    mp3_duration_seconds,
    write_flac,
    write_mp3,
    write_mp4,
    write_ogg,
    write_wav,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "totalAudioDurationCalculator.py"


def run_script(directory, *extra, cwd=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(directory), *extra],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def rendered(seconds):
    text = str(datetime.timedelta(seconds=round(seconds)))
    return f"Total duration:\n{text}\n"


def test_totals_common_formats_by_default(tmp_path):
    write_wav(tmp_path / "chapter.wav", 1)
    write_flac(tmp_path / "chapter.flac", 2)
    write_mp4(tmp_path / "chapter.m4a", 3)
    write_mp4(tmp_path / "chapter.mp4", 4)
    write_ogg(tmp_path / "chapter.ogg", 5)
    write_mp4(tmp_path / "chapter.m4b", 6)
    write_ogg(tmp_path / "chapter.oga", 7)
    mp3_seconds = write_mp3(tmp_path / "chapter.mp3")

    result = run_script(tmp_path)

    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout == rendered(
        1 + 2 + 3 + 4 + 5 + 6 + 7 + mp3_seconds
    )
    assert mp3_seconds == mp3_duration_seconds()


def test_extension_matching_is_case_insensitive(tmp_path):
    write_wav(tmp_path / "One.WAV", 1)
    write_flac(tmp_path / "Two.Flac", 2)
    write_mp4(tmp_path / "Three.M4A", 3)
    write_ogg(tmp_path / "café.OGG", 4)

    result = run_script(tmp_path)

    assert result.returncode == 0
    assert result.stdout == rendered(10)


def test_extensions_flag_limits_which_files_are_counted(tmp_path):
    write_wav(tmp_path / "keep.wav", 2)
    write_flac(tmp_path / "skip.flac", 9)
    write_mp3(tmp_path / "skip.mp3")

    only_flac = run_script(tmp_path, "--extensions", "flac")
    only_mp3 = run_script(tmp_path, "-e", "mp3")

    assert only_flac.returncode == 0
    assert only_flac.stdout == rendered(9)
    assert only_mp3.returncode == 0
    assert only_mp3.stdout == rendered(mp3_duration_seconds())


def test_extensions_flag_accepts_dots_spaces_case_and_repeats(tmp_path):
    write_wav(tmp_path / "a.wav", 2)
    write_flac(tmp_path / "b.flac", 5)
    write_ogg(tmp_path / "c.ogg", 8)

    dotted = run_script(tmp_path, "-e", ".Wav, FLAC")
    repeated = run_script(tmp_path, "-e", "ogg", "-e", "ogg, wav")

    assert dotted.returncode == 0
    assert dotted.stdout == rendered(7)
    assert repeated.returncode == 0
    assert repeated.stdout == rendered(10)


def test_unreadable_files_are_skipped(tmp_path):
    write_wav(tmp_path / "good.wav", 3)
    (tmp_path / "a-bad.mp3").write_bytes(b"this is not an mp3")
    (tmp_path / "m-bad.flac").write_bytes(b"fLaCnot-really")
    (tmp_path / "bad café.mp3").write_bytes(b"nope")

    result = run_script(tmp_path)

    assert result.returncode == 0
    assert result.stdout == rendered(3)
    assert "Traceback" not in result.stderr
    assert "Skipping a-bad.mp3:" in result.stderr
    assert "Skipping m-bad.flac:" in result.stderr
    assert "Skipping bad café.mp3:" in result.stderr
    assert result.stderr.index("a-bad.mp3") < result.stderr.index("m-bad.flac")


def test_directory_of_only_unreadable_files_totals_zero(tmp_path):
    (tmp_path / "broken.m4a").write_bytes(b"")

    result = run_script(tmp_path)

    assert result.returncode == 0
    assert result.stdout == "Total duration:\n0:00:00\n"
    assert "Skipping broken.m4a:" in result.stderr
    assert "Traceback" not in result.stderr


def test_rounds_the_cumulative_total_once(tmp_path):
    # 0.4 + 0.4 = 0.8, which rounds to 1. Rounding each file first would be 0.
    write_wav(tmp_path / "a.wav", 0.4)
    write_wav(tmp_path / "b.wav", 0.4)

    result = run_script(tmp_path)

    assert result.stdout == "Total duration:\n0:00:01\n"


def test_formats_durations_over_an_hour(tmp_path):
    write_flac(tmp_path / "long.flac", 3661)

    result = run_script(tmp_path)

    assert result.stdout == "Total duration:\n1:01:01\n"


def test_ignores_other_files_and_subdirectories(tmp_path):
    write_wav(tmp_path / "top.wav", 2)
    (tmp_path / "notes.txt").write_text("not audio")
    (tmp_path / "folder.mp3").mkdir()
    nested = tmp_path / "parts"
    nested.mkdir()
    write_flac(nested / "nested.flac", 30)

    result = run_script(".", cwd=tmp_path)

    assert result.returncode == 0
    assert result.stdout == rendered(2)
    assert result.stderr == ""


def test_empty_directory(tmp_path):
    result = run_script(tmp_path)

    assert result.returncode == 0
    assert result.stdout == "Total duration:\n0:00:00\n"
    assert result.stderr == ""


def test_missing_or_non_directory_is_an_error(tmp_path):
    missing = run_script(tmp_path / "nope")
    write_wav(tmp_path / "file.wav", 1)
    not_dir = run_script(tmp_path / "file.wav")

    assert missing.returncode == 1
    assert "No such directory:" in missing.stderr
    assert "Traceback" not in missing.stderr
    assert "Total duration:" not in missing.stdout

    assert not_dir.returncode == 1
    assert "Not a directory:" in not_dir.stderr
    assert "Traceback" not in not_dir.stderr
    assert "Total duration:" not in not_dir.stdout


def test_usage_and_help():
    missing_args = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
    )
    help_text = subprocess.run(
        [sys.executable, str(SCRIPT), "-h"],
        capture_output=True,
        text=True,
    )
    empty_ext = subprocess.run(
        [sys.executable, str(SCRIPT), ".", "-e", " , "],
        capture_output=True,
        text=True,
    )

    assert missing_args.returncode != 0
    assert "directory" in missing_args.stderr.lower()
    assert help_text.returncode == 0
    assert "--extensions" in help_text.stdout
    assert "flac" in help_text.stdout
    assert "m4a" in help_text.stdout
    assert empty_ext.returncode != 0


def test_custom_extension_is_read_when_requested(tmp_path):
    wav_path = tmp_path / "chapter.wav"
    write_wav(wav_path, 4)
    (tmp_path / "chapter.xyz").write_bytes(wav_path.read_bytes())

    result = run_script(tmp_path, "-e", "xyz")

    assert result.returncode == 0
    assert result.stdout == rendered(4)
    assert result.stderr == ""


def test_mp3_only_folder_keeps_the_original_stdout(tmp_path):
    seconds = write_mp3(tmp_path / "part.mp3")

    result = run_script(tmp_path)

    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout == rendered(seconds)
    assert result.stdout.startswith("Total duration:\n")
