
from termcolor import colored

from .audio_file import AudioFile
from ..enums import MediaLengthType, Orientation

class VideoFile(AudioFile):

    duration_def = [
        ((0, 300), MediaLengthType.S),  # < 5m
        ((300, 1800), MediaLengthType.M),  # 5m <= d < 30m
        ((1800, 3600), MediaLengthType.L),  # 30m <= d < 60
        ((3600, 3600000), MediaLengthType.XL),  # 60m <= 
    ]

    def __init__(
            self,
            path: str,
            *,
            auto_probe: bool = False,
            preassigned_attrs = {}
    ):
        self.height: None | int = None
        self.width: None | int = None
        self.orientation: Orientation = Orientation.NA

        super().__init__(path, auto_probe=auto_probe, preassigned_attrs=preassigned_attrs)


    def _parse_probe_info(self, probe):
        """Parse the probe info and populate fields"""

        # NOTE that we don't want to call super() here as video stream is a separate one
        
        video_streams = [stream for stream in probe["streams"] if stream["codec_type"] == "video"]
        if len(video_streams) > 1:
            print(f'Warning: found more than 1 video stream in file {colored(self.path, "yellow")},'
                    ' use the first one')

        if len(video_streams) < 1:
            print(f'Warning: failed to find video stream in file {colored(self.path, "yellow")},'
                    ' skip this file')
            self.broken = True
            return

        vs = video_streams[0]
        height = self._coalesce(vs, 'height', 'coded_height')
        width = self._coalesce(vs, 'width', 'coded_width')

        if height is None or width is None:
            print(f'[Warning] Cannot extract the video dimension for file'
                    f' {colored(self.path, "yellow")}')
        else:
            self.height = height
            self.width = width

        duration = vs.get('duration', None)
        if duration is None:
            print(f'[Warning] Cannot extract the video duration for file'
                    f' {colored(self.path, "yellow")}')
        else:
            self.duration = float(duration)


        self._set_length_type()
        self._set_orientation()


    @staticmethod
    def _coalesce(_dict, *args):
        for k in args:
            ret = _dict.get(k, None)
            if ret is not None:
                return ret
        return None

    def _set_orientation(self):

        if self.height is None or self.width is None:
            pass
        else:
            if self.height > self.width:
                self.orientation = Orientation.PORT
            else:
                self.orientation = Orientation.LAND
