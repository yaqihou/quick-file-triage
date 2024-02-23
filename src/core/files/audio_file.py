
import ffmpeg
from termcolor import colored

from .file import File
from ..enums import Category, MediaLengthType, Orientation 

class AudioFile(File):

    duration_def = [
        ((0, 300), MediaLengthType.S),  # < 5m
        ((300, 600), MediaLengthType.M),  # 5m <= d < 10m
        ((600, 1800), MediaLengthType.L),  # 10m <= d < 30
        ((1800, 3600000), MediaLengthType.XL),  # 30m <= 
    ]

    def __init__(
            self,
            path: str,
            *,
            auto_probe: bool = False,
            preassigned_attrs = {}
    ):

        self.duration: None | float = None
        self.length_type: MediaLengthType = MediaLengthType.NA
        self.broken: bool = False

        super().__init__(path, auto_probe=auto_probe, preassigned_attrs=preassigned_attrs)

    def _probe(self):
        """Populate the media metadata fields"""
        try:
            probe = ffmpeg.probe(self.path)
        except:
            print(f'Warning: failed to probe the information of media file'
                  f' {colored(self.path, "yellow")}')
            self.broken = True
        else:
            self._parse_probe_info(probe)

        self.probed = True

    def _parse_probe_info(self, probe):
        """Parse the probe info and populate fields"""

        audio_streams = [stream for stream in probe["streams"] if stream["codec_type"] == "audio"]
        if len(audio_streams) > 1:
            print(f'Warning: found more than 1 audio stream in file {colored(self.path, "yellow")},'
                    ' use the first one')

        if len(audio_streams) < 1:
            print(f'Warning: failed to find audio stream in file {colored(self.path, "yellow")},'
                    ' skip this file')
            self.broken = True
            return

        stream = audio_streams[0]
        duration = stream.get('duration', None)
        if duration is None:
            print(f'[Warning] Cannot extract the video duration for file'
                    f' {colored(self.path, "yellow")}')
        else:
            self.duration = float(duration)

        self._set_length_type()


    def _set_length_type(self):
        if self.duration is not None:
            for (lo, hi), _type in self.duration_def:
                if self.duration >= lo and self.duration < hi:
                    self.length_type = _type
                    return

