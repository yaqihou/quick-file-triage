
from functools import total_ordering
import os
from enum import Enum

class Category(Enum):
    VIDEO = {'.m4v', '.mp4', '.mov', '.mkv', '.wmv', '.asf', '.rm'}
    IMAGE = {'.jpg', '.jpeg', '.png', '.gif'}
    AUDIO = {'.mp3'}
    TXT = {'.txt', '.pdf', '.docx'}
    ZIP = {'.rar', '.zip', '.7z', *[f'.z{x:02d}' for x in range(1, 100)]}
    NA = {}

    @staticmethod
    def infer(name):

        _, ext = os.path.splitext(name)
        ext = ext.lower()
        for cat in Category:
            if ext in cat.value:  return cat
        return Category.NA

@total_ordering
class OrderedEnum(Enum):

    def __lt__(self, other):
        if self.__class__ == other.__class__:
            return self.value < other.value
        raise NotImplementedError(f"Cannot compare class {self.__class__} and {other.__class__}")

class VideoOrientation(OrderedEnum):

    PORT = 'Po'
    LAND = 'La'
    NA = ''


class VideoLengthType(OrderedEnum):

    S = 'S'
    M = 'M'
    L = 'L'
    XL = 'XL'
    NA = ''


class ImageOrientation(OrderedEnum):

    PORT = 'Po'
    LAND = 'La'
    NA = ''

class ImageType(OrderedEnum):

    ILLUST = '@illustration'
    PHOTO = '@photo'
    NOTSURE = '@uncertain'
    NA = '@notset'


class SortAttr(Enum):

    NAME = "name"
    CATEGORY = "cat"
    DATE = "mdate"
    TIME = "mtime"
    SIZE = "size"
    
    # image / video
    WIDTH = 'width'
    HEIGHT = 'height'
    ORIENTATION = 'orientation'

    # video only
    DURATION = 'duration'
    LENGTH_TYPE = 'length_type'

    # image only
    IMAGE_TYPE = 'image_type'


    
