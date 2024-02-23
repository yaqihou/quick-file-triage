
from termcolor import colored

from .file import File
from ..enums import Orientation, ImageType
from ..anime_or_not.anime_or_not import analysis_image

class ImageFile(File):

    def __init__(
            self,
            path: str,
            *,
            auto_probe: bool = False,
            preassigned_attrs = {}
    ):

        self.height: None | int = None
        self.width: None | int = None

        self.image_type: ImageType = ImageType.NA
        self._image_type_prob: float = 0.
        self.orientation: Orientation = Orientation.NA

        super().__init__(path, auto_probe=auto_probe, preassigned_attrs=preassigned_attrs)
        
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
        self.probed = True

    def _set_orientation(self):

        if self.height is None or self.width is None:
            pass
        else:
            if self.height > self.width:
                self.orientation = Orientation.PORT
            else:
                self.orientation = Orientation.LAND
