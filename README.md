# Total Audio Duration Calculator

Small Python script that totals the duration of audio files in a directory. It is useful for figuring out the length of an audiobook that is split into parts.

Files are read from the directory you pass in. Subfolders are not scanned. The total is rounded to the nearest second and printed as `H:MM:SS`.

```
Total duration:
1:23:45
```

## Supported formats

By default the script includes these extensions. Matching is case-insensitive, so `Track.FLAC` and `track.flac` are both counted:

`mp3`, `flac`, `m4a`, `m4b`, `mp4`, `wav`, `ogg`, `oga`, `opus`, `aac`, `aiff`, `aif`, `wma`, `wv`, `ape`

Durations come from [mutagen](https://github.com/quodlibet/mutagen). You can name any other extension with `--extensions`; mutagen will try to read it. A file that cannot be read is skipped, with a message on stderr, and the rest of the directory is still totaled.

Folders that contain only MP3 files produce the same total as earlier versions of this script. Pass `-e mp3` to ignore every other format.

## Install

Python 3.9 or newer:

```bash
pip install -r requirements.txt
```

## Usage

```bash
python totalAudioDurationCalculator.py /path/to/directory
```

Count only some types. Names can include a leading dot, and the flag can be repeated:

```bash
python totalAudioDurationCalculator.py /path/to/directory --extensions flac,m4a
python totalAudioDurationCalculator.py /path/to/directory -e mp3
python totalAudioDurationCalculator.py /path/to/directory -e .wav -e ogg
```

```bash
python totalAudioDurationCalculator.py --help
```

## Tests

Tests generate tiny synthetic audio files while they run. No audio is stored in the repository.

```bash
pip install -r requirements-dev.txt
pytest
```

GitHub Actions runs the same tests on pushes and pull requests.
