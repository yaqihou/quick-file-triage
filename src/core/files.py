
import os
import ffmpeg
import datetime as dt
from dataclasses import dataclass
from termcolor import colored

from .enums import Category, VideoLengthType, VideoOrientation, ImageOrientation, ImageType
from .anime_or_not.anime_or_not import analysis_image

@dataclass
class File():

    path: str
    probe_on: bool = False

    def __post_init__(self):
        self.name: str = os.path.basename(self.path)
        self.cat: Category = Category.infer(self.name)

        _fstat = os.stat(self.path) 
        self.mtime = dt.datetime.fromtimestamp(_fstat.st_mtime)
        self.mdate = self.mtime.date()
        self.size = _fstat.st_size
    
    def update_path(self, new_path):
        self.path = new_path

    def move(self, dst, verbose=False, dry_run=False):
        if dry_run:
            print(f'Will move {colored(self.path, "yellow")}\n    -> {colored(dst, "green")}')

        if not dry_run:
            if verbose:
                print(f'Moving {self.path} -> {dst}')
            os.rename(self.path, dst)
            self.update_path(dst)

    def __eq__(self, other):
        return ((self.name == other.name)
                and (self.mtime == other.mtime)
                and (self.size == other.size)
                )


@dataclass
class VideoFile(File):

    probe_on: bool = True

    height: None | int = None
    width: None | int = None
    duration: None | float = None

    length_type: VideoLengthType = VideoLengthType.NA
    orientation: VideoOrientation = VideoOrientation.NA

    # TODO - add suppot to move "possible" broken files to somewhere
    broken: bool = False

    duration_def = [
        ((0, 300), VideoLengthType.S),  # < 5m
        ((300, 1800), VideoLengthType.M),  # 5m <= d < 30m
        ((1800, 3600), VideoLengthType.L),  # 30m <= d < 60
        ((3600, 3600000), VideoLengthType.XL),  # 60m <= 
    ]

    def __post_init__(self):
        super().__post_init__()

        if self.probe_on:
            self._probe()
        
    def _probe(self):
        """Populate the video metadata fields"""
        try:
            probe = ffmpeg.probe(self.path)
        except:
            print(f'Warning: failed to probe the information of file'
                  f' {colored(self.path, "yellow")}')
            self.broken = True
        else:
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

    @staticmethod
    def _get_sec_str(s):
        h = int(s // 3600)
        s = s % 3600

        m = int(s // 60)
        s = int(s % 60)
        return f'{h:02d}:{m:02d}:{s:02d}'

    def _set_orientation(self):

        if self.height is None or self.width is None:
            pass
        else:
            if self.height > self.width:
                self.orientation = VideoOrientation.PORT
            else:
                self.orientation = VideoOrientation.LAND
        
    def _set_length_type(self):
        if self.duration is not None:
            for (lo, hi), _type in self.duration_def:
                if self.duration >= lo and self.duration < hi:
                    self.length_type = _type
                    return


@dataclass
class ImageFile(File):

    probe_on: bool = True

    height: None | int = None
    width: None | int = None

    image_type: ImageType = ImageType.NA
    _image_type_prob: float = 0.
    orientation: ImageOrientation = ImageOrientation.NA

    def __post_init__(self):
        super().__post_init__()

        if self.probe_on:
            self._probe()
        
    def _probe(self):
        """Populate the video metadata fields"""
        try:
            prob, width, height = analysis_image(self.path)
        except:
            print(f'Warning: failed to probe the information of file'
                  f' {colored(self.path, "yellow")}')
        else:
            # NOTE - prob is in percentage
            self._image_type_prob = prob
            if prob >= 65:
                self.image_type = ImageType.ILLUST
            elif prob > 35:
                self.image_type = ImageType.NOTSURE
            else:
                self.image_type = ImageType.PHOTO

            self.width, self.height = width, height

        self._set_orientation()

    def _set_orientation(self):

        if self.height is None or self.width is None:
            pass
        else:
            if self.height > self.width:
                self.orientation = ImageOrientation.PORT
            else:
                self.orientation = ImageOrientation.LAND
