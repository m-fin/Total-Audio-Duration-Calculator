import os
import sys
import datetime
from mutagen.mp3 import MP3


def main():
    if len(sys.argv) != 2:
        print("Format: audiolength.py [/Path/To/Directory]")
    else:
        print("Total duration:")
        print(getTotalAudioDuration(sys.argv[1]))


def getTotalAudioDuration(path):
    # Get absoulte path from relative path
    absolutePath = os.path.abspath(path)

    # cd to directory
    os.chdir(absolutePath)

    # Take cumulative sum of each audio file's duration in seconds
    cumulativeDuration = 0
    for entry in os.listdir(absolutePath):
        if os.path.isfile(os.path.join(absolutePath, entry)):
            if entry.endswith('.mp3'):
                entryDuration = (MP3(entry).info.length)
                cumulativeDuration += entryDuration

    # Round cumulative duration
    roundedCumulativeDuration = round(cumulativeDuration)

    return str(datetime.timedelta(seconds=roundedCumulativeDuration))


if __name__ == '__main__':
    main()
