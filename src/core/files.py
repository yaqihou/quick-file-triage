
import os
import ffmpeg
import datetime as dt
from termcolor import colored

from .enums import Category, VideoLengthType, VideoOrientation, ImageOrientation, ImageType, Enum
from .anime_or_not.anime_or_not import analysis_image

# TODO - modify the anime_or_not to support 4-channel (alpha) PNG files

class File():

    def __init__(
            self,
            path: str,
            probe_on: bool = False,
            preassigned_attrs = {}
    ):

        self.path: str = path
        self.probe_on: bool = probe_on

        self.name: str
        self.cat: Category 

        self.mtime: dt.datetime
        self.mdate: dt.date 
        self.size: float 

        if not preassigned_attrs:
            self._setup_attr()
        else:
            for attr, val in preassigned_attrs.items():
                setattr(self, attr, val)

    def _setup_attr(self):

        self.name: str = os.path.basename(self.path)
        self.cat: Category = Category.infer(self.name)

        _fstat = os.stat(self.path) 
        self.mtime: dt.datetime = dt.datetime.fromtimestamp(_fstat.st_mtime)
        self.mdate: dt.date = self.mtime.date()
        self.size: float = _fstat.st_size 
    
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

    def to_dict(self):
        """Store attribute in form of dictionary for pickling"""
        # return {attr: getattr(self, attr) for attr in self._attr_register}
        return {k: v.name if isinstance(v, Enum) else v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, prop_dict):
        path = prop_dict['path']
        probe_on = prop_dict['probe_on']
        other_fields = {k: v for k, v in prop_dict.items()
                        if k not in ['path', 'probe_on']}
        return cls(path, probe_on, other_fields)

class VideoFile(File):

    duration_def = [
        ((0, 300), VideoLengthType.S),  # < 5m
        ((300, 1800), VideoLengthType.M),  # 5m <= d < 30m
        ((1800, 3600), VideoLengthType.L),  # 30m <= d < 60
        ((3600, 3600000), VideoLengthType.XL),  # 60m <= 
    ]

    def __init__(self, path: str, probe_on: bool = False,
                 preassigned_attrs = {}
                 ):
        self.height: None | int
        self.width: None | int
        self.duration: None | float

        self.length_type: VideoLengthType
        self.orientation: VideoOrientation

        self.broken: bool = False

        super().__init__(path, probe_on, preassigned_attrs=preassigned_attrs)


    def _setup_attr(self):
        super()._setup_attr()

        self.height = None
        self.width = None
        self.duration = None

        self.length_type = VideoLengthType.NA
        self.orientation = VideoOrientation.NA

        self.broken: bool = False

        if self.probe_on:
            self._probe()
        
        
    def _probe(self):
        """Populate the video metadata fields"""
        try:
            probe = ffmpeg.probe(self.path)
        except:
            print(f'Warning: failed to probe the information of video'
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


class ImageFile(File):

    def __init__(self, path: str, probe_on: bool = False,
                 preassigned_attrs = {}):

        self.height: None | int
        self.width: None | int

        self.image_type: ImageType
        self._image_type_prob: float
        self.orientation: ImageOrientation

        super().__init__(path, probe_on, preassigned_attrs)

    def _setup_attr(self):
        super()._setup_attr()

        self.height =  None
        self.width = None

        self.image_type = ImageType.NA
        self._image_type_prob = 0.
        self.orientation = ImageOrientation.NA

        if self.probe_on:
            self._probe()
        
    def _probe(self):
        """Populate the video metadata fields"""
        try:
            prob, width, height = analysis_image(self.path)
        except:
            print(f'Warning: failed to probe the information of image'
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


class FileFactory:
    _reg = {
        Category.VIDEO: VideoFile,
        Category.IMAGE: ImageFile,
        Category.AUDIO: File,
        Category.TXT: File,
        Category.ZIP: File,
        Category.NA: File,
    }

    @classmethod
    def get(cls, cat: Category) -> File:
        return cls._reg[cat]
