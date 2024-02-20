
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


class VideoOrientation(Enum):

    PORT = 'Po'
    LAND = 'La'
    NA = ''


class VideoLengthType(Enum):

    S = 'S'
    M = 'M'
    L = 'L'
    XL = 'XL'
    NA = ''


class ImageOrientation(Enum):

    PORT = 'Po'
    LAND = 'La'
    NA = ''

class ImageType(Enum):

    ILLUST = 'Illustration'
    PHOTO = 'Photo'
    NOTSURE = 'NotSure'
    NA = ''
