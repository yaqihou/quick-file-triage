
import os
import datetime as dt
from tqdm import tqdm
from termcolor import colored
import subprocess as sp
from tabulate import tabulate

from .enums import Category, ImageOrientation, ImageType, VideoOrientation, VideoLengthType
from .files import File, ImageFile, VideoFile
from .utils import get_readable_filesize


class FileList():

    _category: Category | None = None
    _play_cmd: list | None = None
    _target_folder: str = "@uncatgorized"

    process_list: list[sp.Popen] = []
    
    def __init__(self, filelist: list[File] = []):

        self.filelist: list[File] = []
        self.mdate_map: dict[dt.date, list[File]] = {}

        for f in sorted(filelist, key=lambda f: f.name):
            self.add_file(f)

    def to_dict(self):
        return {f.path: f for f in self.filelist}

    @property
    def category(self):
        if self._category is None:
            return Category.NA.name
        return self._category.name

    def namelist_iter(self):
        for f in self.filelist:
            yield f.name

    def path_iter(self):
        for f in self.filelist:
            yield f.path

    def __del__(self):
        FileList.process_list = [p for p in FileList.process_list if p.poll() is None]

    def __len__(self):
        return len(self.filelist)

    @property
    def len(self):
        return self.__len__()

    # TODO
    def add_from_path(self, path):
        pass

    def add_file(self, f: File):
        self.filelist.append(f)

        self.mdate_map.setdefault(f.mdate, [])
        self.mdate_map[f.mdate].append(f)

    def by_mdate(self, date: dt.date):
        if date in self.mdate_map:
            return self.__class__(filelist=self.mdate_map[date])
        else:
            print(f'Warning: given date {date} is not in current file list')
            return self.__class__()

    @property
    def mdates(self):
        return list(sorted(list(self.mdate_map.keys())))

    @classmethod
    def _popen(cls, cmd):
        p = sp.Popen(cmd, stdout=sp.DEVNULL, stderr=sp.DEVNULL)
        FileList.process_list.append(p)

    def open(self, *args, top: None | int = None, **kwargs):
        """Open first <top> / all files in default app"""
        raise NotImplementedError(f'Open all is not implemented for files of {self.category} type ')

    def _get_dst(self, f: File, dst_folder: str):
        return os.path.join(dst_folder, f.name)

    def organize(self, verbose=True, dry_run=False):
        if self._target_folder is None:
            print("No target folder defined to organize the file into")
        else:
            self._organize(verbose, dry_run)

    def _organize(self, verbose, dry_run):
        """Default organize behaviour"""

        dst_folder = self._target_folder
        self.move_to(dst_folder, verbose=verbose, dry_run=dry_run)

    @staticmethod
    def _prepare_dir(folder):
        if not os.path.exists(folder):
            print(f'Destination folder {colored(folder, "green")} does not exist, creating it now...')
            os.makedirs(folder)

    def move_to(self, dst_folder, verbose=True, dry_run=False):
        existed_file_list = []
        to_move_list = []
        for f in self.filelist:
            dst = self._get_dst(f, dst_folder)

            if f.path == dst:  continue

            if os.path.isfile(dst):
                existed_file_list.append((f, dst))
            else:
                to_move_list.append((f, dst))
            
        if existed_file_list:
            # TODO - Add md5sum check
            print("The following files already exists:")
            for f, dst in existed_file_list:
                print(colored(f.name, 'yellow'))
                print(f'   - [{get_readable_filesize(f.size)}] {f.path}')
                print(f'   + [{get_readable_filesize(os.path.getsize(dst))}] {dst}')

            # TODO - Add one-by-one selection and overwrite mode
            prompt = input('What action wolud you like? *[S]kip / [R]ename / [Q]uit').lower()

            if prompt in ['s', '']:
                pass  # Do nothing
            elif prompt == 'r':
                print('Duplicated files will be renamed as')
                for f, dst in existed_file_list:
                    new_dst = self.get_uniq_dst(dst)
                    to_move_list.append((f, new_dst))
                    print(f.path)
                    print('  -->', new_dst)
            else:
                exit()

        if to_move_list:
            self._prepare_dir(dst_folder)

            for f, dst in tqdm(to_move_list, desc=f"{self.category} moving"):
                f.move(dst, dry_run=dry_run, verbose=verbose)

        return

    @staticmethod
    def get_uniq_dst(dst):
        """Add suffix to dst to create unique filename"""

        folder = os.path.dirname(dst)
        base, ext = os.path.splitext(os.path.basename(dst))

        suffix = 0
        while os.path.isfile(os.path.join(folder, f"{base}-{suffix}{ext}")):
            suffix += 1

        return os.path.join(folder, f"{base}-{suffix}{ext}")

    def summary(self):
        print(f"{self.category} file counts: {len(self.filelist)}")

    def details(self, show_path=False):

        for f in self.filelist:
            _path_str = f" ({f.path})" if show_path else ""
            print(f'    - {colored(f.name, "green")}{colored(_path_str, "yellow")}')

        print('=' * 40)
        self.summary()


class VideoFileList(FileList):

    _category = Category.VIDEO
    _target_folder = "@video"

    def __init__(self, filelist: list[VideoFile] = []):
        self.orientation_map: dict[VideoOrientation, list[VideoFile]] = {
            ori: [] for ori in VideoOrientation
        }
        self.length_type_map: dict[VideoLengthType, list[VideoFile]] = {
            lt: [] for lt in VideoLengthType
        }
        super().__init__(filelist)

        self.filelist: list[VideoFile]

    @property
    def shorts(self):
        return self.by_length_type(VideoLengthType.S)

    @property
    def mids(self):
        return self.by_length_type(VideoLengthType.M)

    @property
    def longs(self):
        return self.by_length_type(VideoLengthType.L)

    @property
    def exlongs(self):
        return self.by_length_type(VideoLengthType.XL)

    @property
    def unknown_length(self):
        return self.by_length_type(VideoLengthType.NA)

    @property
    def portrait(self):
        return self.by_orientation(VideoOrientation.PORT)

    @property
    def landscape(self):
        return self.by_orientation(VideoOrientation.LAND)

    @property
    def unknown_ratio(self):
        return self.by_orientation(VideoOrientation.NA)

    def open(self,
             top: None | int = None,
             orientation: None | VideoOrientation = None,
             length_type: None | VideoLengthType = None
             ):
        """Open first <top> / all files in default app"""

        if orientation is None and length_type is None:
            cmd = ['vlc', '--'] + list(self.path_iter())[:top]
            FileList._popen(cmd)
        elif orientation is None and length_type is not None:
            self.by_length_type(length_type).open(top=top)
        elif orientation is not None and length_type is None:
            self.by_orientation(orientation).open(top=top)
        else:
            assert length_type is not None
            assert orientation is not None
            self.by_length_type(length_type).by_orientation(orientation).open(top=top)


    def add_file(self, f: VideoFile):

        if f.probe_on and f.broken:
            _folder = '@broken-videos'
            self._prepare_dir(_folder)
            dst = self.get_uniq_dst(os.path.join(_folder, f.name))
            f.move(os.path.join(dst))
        else:

            super().add_file(f)
            self.orientation_map[f.orientation].append(f)
            self.length_type_map[f.length_type].append(f)

    def by_length_type(self, length_type: VideoLengthType):
        return self.__class__(self.length_type_map[length_type])

    def by_orientation(self, orientation: VideoOrientation):
        return self.__class__(self.orientation_map[orientation])

    def _get_dst(self, f: VideoFile, dst_folder: str):

        _prefix = (f.length_type.value, f.orientation.value)
        if _prefix == ('', ''):
            prefix = ""
        else:
            _a = '_' if not _prefix[0] else _prefix[0]
            _b = '_' if not _prefix[1] else _prefix[1]
            prefix = f'[{_a}-{_b}]'

        # Avoid duplicate prefix or when probe is turned off
        if f.name.startswith(prefix) or not f.probe_on:
            prefix = ""

        return os.path.join(dst_folder, prefix + f.name)

    def _organize(self, verbose, dry_run):

        for mdate in self.mdates:
            dst_folder = os.path.join(self._target_folder, str(mdate))
            self.by_mdate(mdate).move_to(dst_folder, verbose=verbose, dry_run=dry_run)

    def summary(self):

        print('Video files summary:')
        summary_table = [
            ["", "Portrait", "Landscape", "Unknown Ratio", "Sum"],
            ["Short", 0, 0, 0, 0],
            ["Medium", 0, 0, 0, 0],
            ["Long", 0, 0, 0, 0],
            ["Ex-Long", 0, 0, 0, 0],
            ["Unknown Length", 0, 0, 0, 0],
            ["Sum", 0, 0, 0, 0]]

        row_map = {
            VideoLengthType.S: 1,
            VideoLengthType.M: 2,
            VideoLengthType.L: 3,
            VideoLengthType.XL: 4,
            VideoLengthType.NA: 5
        }

        col_map = {
            VideoOrientation.PORT: 1,
            VideoOrientation.LAND: 2,
            VideoOrientation.NA: 3
        }

        for f in self.filelist:
           row = row_map[f.length_type]
           col = col_map[f.orientation]

           summary_table[row][col] += 1
           summary_table[row][-1] += 1
           summary_table[-1][col] += 1
           summary_table[-1][-1] += 1

        print(tabulate(summary_table))

        

class AudioFileList(FileList):

    _category = Category.AUDIO
    _target_folder = "@audio"

    def open(self, top: None | int = None):
        """Open first <top> / all files in default app"""
        cmd = ['vlc', '--'] + list(self.path_iter())[:top]
        FileList._popen(cmd)

    pass

class ImageFileList(FileList):

    _category = Category.IMAGE
    _target_folder = '@image'

    def __init__(self, filelist: list[ImageFile] = []):
        self.orientation_map: dict[ImageOrientation, list[ImageFile]] = {
            ori: [] for ori in ImageOrientation
        }
        self.image_type_map: dict[ImageType, list[ImageFile]] = {
            _type: [] for _type in ImageType
        }
        super().__init__(filelist)

        self.filelist: list[ImageFile]

    @property
    def illustrations(self):
        return self.by_image_type(ImageType.ILLUST)

    @property
    def photos(self):
        return self.by_image_type(ImageType.PHOTO)

    @property
    def other(self):
        return self.by_image_type(ImageType.NOTSURE)

    @property
    def portrait(self):
        return self.by_orientation(ImageOrientation.PORT)

    @property
    def landscape(self):
        return self.by_orientation(ImageOrientation.LAND)

    @property
    def unknown_ratio(self):
        return self.by_orientation(ImageOrientation.NA)

    def open(self,
             top: None | int = None,
             orientation: None | ImageOrientation = None,
             image_type: None | ImageType = None
             ):
        """Open first <top> / all files in default app"""
        
        if orientation is None and image_type is None:
            cmd = ['feh', '-g', '1680x1050', '--scale-down', '--auto-zoom'] + list(self.path_iter())[:top]
            FileList._popen(cmd)
        elif orientation is None and image_type is not None:
            self.by_image_type(image_type).open(top=top)
        elif orientation is not None and image_type is None:
            self.by_orientation(orientation).open(top=top)
        else:
            self.by_image_type(image_type).by_orientation(orientation).open(top=top)

    def _organize(self, verbose, dry_run):

        for mdate in self.mdates:
            for image_type in ImageType:
                dst_folder = os.path.join(self._target_folder, image_type.value, str(mdate))
                self.by_mdate(mdate)\
                    .by_image_type(image_type)\
                    .move_to(dst_folder, verbose=verbose, dry_run=dry_run)
        
    def add_file(self, f: ImageFile):
        super().add_file(f)
        self.orientation_map[f.orientation].append(f)
        self.image_type_map[f.image_type].append(f)

    # TODO - make this accept general arguments (like a few types)
    def by_image_type(self, image_type: ImageType):
        return self.__class__(self.image_type_map[image_type])

    def by_orientation(self, orientation: ImageOrientation):
        return self.__class__(self.orientation_map[orientation])

    def summary(self):

        print('Image files summary:')
        summary_table = [
            ["", "Portrait", "Landscape", "Unknown Ratio", "Sum"],
            ["Illustration", 0, 0, 0, 0],
            ["Photo", 0, 0, 0, 0],
            ["Uncertain", 0, 0, 0, 0],
            ["Type Not Set", 0, 0, 0, 0],
            ["Sum", 0, 0, 0, 0]]

        row_map = {
            ImageType.ILLUST: 1,
            ImageType.PHOTO: 2,
            ImageType.NOTSURE: 3,
            ImageType.NA: 4
        }

        col_map = {
            ImageOrientation.PORT: 1,
            ImageOrientation.LAND: 2,
            ImageOrientation.NA: 3
        }

        for f in self.filelist:
           row = row_map[f.image_type]
           col = col_map[f.orientation]

           summary_table[row][col] += 1
           summary_table[row][-1] += 1
           summary_table[-1][col] += 1
           summary_table[-1][-1] += 1

        print(tabulate(summary_table))

class TXTFileList(FileList):

    _category = Category.TXT
    _target_folder = '@document'


class ZIPFileList(FileList):

    _category = Category.ZIP
    _target_folder = '@compressed'
