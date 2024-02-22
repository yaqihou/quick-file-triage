
import os
from random import shuffle
import datetime as dt
from tqdm import tqdm
from termcolor import colored
import subprocess as sp
from tabulate import SEPARATING_LINE, tabulate

from .enums import Category, ImageType, SortAttr, Orientation, MediaLengthType
from .files import AudioFile, File, ImageFile, VideoFile
from .utils import MinType, get_readable_filesize, parse_sec_to_str

# TODO - support general query search
# TODO - add random play support for open

class FileList():

    _category: Category = Category.NA
    _open_file_cmd_lst: list[str] = []
    _target_folder: str = "@uncatgorized"
    _file_type: type = File

    process_list: list[sp.Popen] = []
    
    def __init__(self, filelist: list[File] = []):

        self.filelist: list[File] = []
        self._folder_keys = {}  # use a dictionary for easier autocomplete
        self.mdate_map: dict[dt.date, list[File]] = {}

        for f in filelist:
            self.add_file(f)

    def to_dict(self):
        return {f.path: f.to_dict() for f in self.filelist}

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

    def add_file(self, path_or_file: str | File, **kwargs):

        if isinstance(path_or_file, str):
            if os.path.isfile(path_or_file):
                f = self._file_type(path_or_file, **kwargs)
            else:
                raise ValueError(f"Given path {path_or_file} doesn't exist")

        elif isinstance(path_or_file, File):
            f = path_or_file

        else:
            raise ValueError(f'Given input {path_or_file} should be a path str or File instance')

        self._add_file(f)


    def add_file_from_cache(self, _dict):
        self._add_file(self._file_type.from_dict(_dict))

    def _add_file(self, f: File):
        self.filelist.append(f)

        # add the folder path to be used in 
        _folder = os.path.dirname(f.path).split(os.sep)
        
        for idx in range(1, len(_folder)+1):
            k = os.sep.join(_folder[:idx])
            self._folder_keys[k] = k

        self.mdate_map.setdefault(f.mdate, [])
        self.mdate_map[f.mdate].append(f)

    @property
    def folders(self):
        return self._folder_keys

    def _get_filelist_by_folder(self, folder_prefix):
        # NOTE Could be optimized if organize it as a tree, but we may want to keep the order as used in .sort()
        return [f for f in self.filelist if f.path.startswith(folder_prefix)]
    
    def by_folder(self, folder_prefix):
        return self.__class__(self._get_filelist_by_folder(folder_prefix))

    # Date time related methods
    def by_mdate(self, date: dt.date):
        return self.by_mdates([date])

    def by_mdates(self, dates: list[dt.date]):
        
        filelist = []
        for mdate in dates:
            if mdate in self.mdate_map:
                filelist += self.mdate_map[mdate]
            else:
                print(f'Warning: found no file on the given date {mdate}')

        if not filelist:
           print('Found no file on the given list of dates')

        return self.__class__(filelist=filelist)

    @property
    def mdates(self):
        return list(sorted(list(self.mdate_map.keys())))

    def today(self):
        today = dt.datetime.today().date()
        if today in self.mdate_map:
            return self.by_mdate(today)
        else:
            print(f"Didn't found any files with modified time as of date {today}")

    def last_days(self, days=5):
        """Return the files from last X existing days"""
        return self.by_mdates(self.mdates[-days:])

    def first_days(self, days=5):
        """Return the files from first X existing days"""
        return self.by_mdates(self.mdates[:days])

    def recent(self, days=5):
        """Return the files from last X days from today"""
        today = dt.datetime.today().date()
        recent_days = [today - dt.timedelta(days=day) for day in range(days+1)]
        return self.by_mdates(recent_days)

    # File opening related methods
    @classmethod
    def _popen(cls, cmd):
        p = sp.Popen(cmd, stdout=sp.DEVNULL, stderr=sp.DEVNULL)
        FileList.process_list.append(p)

    def _open(self,
              cmd_lst: list[str],
              top: None | int = None,
              random: bool = False,
              *,
              path_lst: None | list[str] = None
              ):
        if path_lst is None:
            _path_lst = self._get_pathlist_to_open(top=top, random=random)
        else:
            _path_lst = path_lst
        print(path_lst)
        cmd = cmd_lst + _path_lst
        FileList._popen(cmd)
        
    def open(self,
             top: None | int = None,
             random: bool = False,
             *,
             path_lst: None | list[str] = None,
             **kwargs):
        """Open first <top> / all files in default app"""
        if self._open_file_cmd_lst:
            self._open(self._open_file_cmd_lst, top=top, random=random, path_lst=path_lst)
        else:
            raise NotImplementedError(f'Open file command not defined for class {self.__class__}')
                

    def _get_pathlist_to_open(
            self,
            top: None | int = None,
            random: bool = False
    ) -> list[str]:
        _lst = list(self.path_iter())[:top]
        if random:  shuffle(_lst)
        return _lst

    # File move / organize related methods

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
            
        # TODO - refactor the overwriting logic here
        if existed_file_list:
            print("The following files already exists:")
            for f, dst in existed_file_list:
                print(colored(f.name, 'yellow'))
                print(f'   - [{get_readable_filesize(f.size)}] {f.path}')
                print(f'   + [{get_readable_filesize(os.path.getsize(dst))}] {dst}')

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

    # Content (stats) show related methods
    def summary(self):
        print(f"{self.category} file counts: {len(self.filelist)}")

    def details(self, show_path=False, color=True):

        data_dict, total_dict = self._get_details_to_show(show_path=show_path, color=color)

        header = list(data_dict.keys())
        data = []

        for idx in range(len(data_dict[header[0]])):
            row = [data_dict[col][idx] for col in header]
            data.append(row)

        # Add total summary
        data.append(SEPARATING_LINE)
        data.append([total_dict.get(col, '') for col in header])


        print(tabulate(data, headers=header))

        return self

    def _get_details_to_show(self, show_path, color):
        data_dict = {
            'Filename': [],
            'Size': [],
            'Date': []
        }

        total_dict = {
            'Filename': f"Total {self.len} files",
            'Size': get_readable_filesize(sum(f.size for f in self.filelist))
        }
        
        if show_path:  data_dict['Path'] = []

        for f in self.filelist:
            data_dict['Filename'].append(
                f.name if not color else colored(f.name, 'green')
            )

            _fsize = get_readable_filesize(f.size)
            data_dict['Size'].append(
                _fsize if not color else colored(_fsize, 'yellow')
            )

            data_dict['Date'].append(
                str(f.mdate) if not color else colored(str(f.mdate), 'blue')
            )
            if show_path:  data_dict['Path'].append(f.path)

        return data_dict, total_dict

    # two alias to details()
    def list(self):
        return self.details()

    def ls(self):
        return self.details()

    def sort(self, attr:SortAttr = SortAttr.NAME):
        def sorter(f):
            if not hasattr(f, attr.value):
                return MinType()
            else:
                return getattr(f, attr.value)
        self.filelist.sort(key=sorter)
        return self


class AudioFileList(FileList):

    _category = Category.AUDIO
    _target_folder = "@audio"
    _open_file_cmd_lst = ['vlc', '--']
    _file_type: type = AudioFile

    def __init__(self, filelist: list[AudioFile] = []):
        self.length_type_map: dict[MediaLengthType, list[AudioFile]] = {
            lt: [] for lt in MediaLengthType
        }
        super().__init__(filelist)

        self.filelist: list[AudioFile]

    @property
    def shorts(self):
        return self.by_length_type(MediaLengthType.S)

    @property
    def mids(self):
        return self.by_length_type(MediaLengthType.M)

    @property
    def longs(self):
        return self.by_length_type(MediaLengthType.L)

    @property
    def exlongs(self):
        return self.by_length_type(MediaLengthType.XL)

    def open(self,
             length_type: None | MediaLengthType = None,
             top: None | int = None,
             random: bool = False,
             *,
             path_lst: None | list[str] = None
             ):
        """Open first <top> / all files in default app"""

        if length_type is None:
            super().open(top=top, random=random, path_lst=path_lst)
        elif length_type is not None:
            self.by_length_type(length_type)\
                .open(top=top, random=random, path_lst=path_lst)
        else:
            raise ValueError('Something wrong with the input')

    def _add_file(self, f: AudioFile):

        if f.probe_on and f.broken:
            _folder = '@broken-audios'
            self._prepare_dir(_folder)
            dst = self.get_uniq_dst(os.path.join(_folder, f.name))
            f.move(os.path.join(dst))

        else:
            super()._add_file(f)
            self.length_type_map[f.length_type].append(f)

    def by_length_type(self, length_type: MediaLengthType):
        return self.__class__(self.length_type_map[length_type])

    def summary(self):

        print('Audio files summary:')
        summary_table = [
            ["", "Sum"],
            ["Short", 0],
            ["Medium", 0],
            ["Long", 0],
            ["Ex-Long", 0],
            ["Unknown Length", 0],
            ["Sum", 0]]

        row_map = {
            MediaLengthType.S: 1,
            MediaLengthType.M: 2,
            MediaLengthType.L: 3,
            MediaLengthType.XL: 4,
            MediaLengthType.NA: 5
        }

        for f in self.filelist:
           row = row_map[f.length_type]

           summary_table[row][1] += 1
           summary_table[-1][1] += 1

        print(tabulate(summary_table))

        return self

    def _get_details_to_show(self, show_path, color):
        data_dict, total_dict = super()._get_details_to_show(show_path, color)

        data_dict['Duration'] = []
        for f in self.filelist:
            data_dict['Duration'].append(parse_sec_to_str(f.duration) if f.duration else "")

        total_dict['Duration'] = parse_sec_to_str(sum(
            f.duration if f.duration else 0
            for f in self.filelist
        ))

        return data_dict, total_dict


class VideoFileList(AudioFileList):

    _category = Category.VIDEO
    _target_folder = "@video"
    _file_type = VideoFile

    def __init__(self, filelist: list[VideoFile] = []):
        self.orientation_map: dict[Orientation, list[VideoFile]] = {
            ori: [] for ori in Orientation
        }
        super().__init__(filelist)

        self.filelist: list[VideoFile]

    @property
    def portrait(self):
        return self.by_orientation(Orientation.PORT)

    @property
    def landscape(self):
        return self.by_orientation(Orientation.LAND)

    @property
    def unknown_ratio(self):
        return self.by_orientation(Orientation.NA)

    def open(self,
             orientation: None | Orientation = None,
             length_type: None | MediaLengthType = None,
             top: None | int = None,
             random: bool = False,
             *,
             path_lst: None | list[str] = None
             ):
        """Open first <top> / all files in default app"""

        if orientation is None and length_type is None:
            super().open(top=top, random=random, path_lst=path_lst)
        elif orientation is None and length_type is not None:
            self.by_length_type(length_type)\
                .open(top=top, random=random, path_lst=path_lst)
        elif orientation is not None and length_type is None:
            self.by_orientation(orientation)\
                .open(top=top, random=random, path_lst=path_lst)
        elif orientation is not None and length_type is not None:
            self.by_length_type(length_type)\
                .by_orientation(orientation)\
                .open(top=top, random=random, path_lst=path_lst)
        else:
            raise ValueError('Something wrong with the input')

    def _add_file(self, f: VideoFile):

        if f.probe_on and f.broken:
            _folder = '@broken-videos'
            self._prepare_dir(_folder)
            dst = self.get_uniq_dst(os.path.join(_folder, f.name))
            f.move(os.path.join(dst))

        else:
            super()._add_file(f)
            self.orientation_map[f.orientation].append(f)

    def by_orientation(self, orientation: Orientation):
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
            MediaLengthType.S: 1,
            MediaLengthType.M: 2,
            MediaLengthType.L: 3,
            MediaLengthType.XL: 4,
            MediaLengthType.NA: 5
        }

        col_map = {
            Orientation.PORT: 1,
            Orientation.LAND: 2,
            Orientation.NA: 3
        }

        for f in self.filelist:
           row = row_map[f.length_type]
           col = col_map[f.orientation]

           summary_table[row][col] += 1
           summary_table[row][-1] += 1
           summary_table[-1][col] += 1
           summary_table[-1][-1] += 1

        print(tabulate(summary_table))

    def _get_details_to_show(self, show_path, color):
        data_dict, total_dict = super()._get_details_to_show(show_path, color)

        data_dict['Height'] = []
        data_dict['Width'] = []
        data_dict['Port/Land'] = []
        for f in self.filelist:
            data_dict['Height'].append(f.height if f.height else "")
            data_dict['Width'].append(f.width if f.width else "")
            data_dict['Port/Land'].append(f.orientation.value)

        total_dict['Duration'] = parse_sec_to_str(sum(
            f.duration if f.duration else 0
            for f in self.filelist
        ))

        return data_dict, total_dict


class ImageFileList(FileList):

    _category = Category.IMAGE
    _target_folder = '@image'
    _open_file_cmd_lst = ['feh', '-g', '1680x1050', '--scale-down', '--auto-zoom']
    _file_type = ImageFile

    def __init__(self, filelist: list[ImageFile] = []):
        self.orientation_map: dict[Orientation, list[ImageFile]] = {
            ori: [] for ori in Orientation
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
        return self.by_orientation(Orientation.PORT)

    @property
    def landscape(self):
        return self.by_orientation(Orientation.LAND)

    @property
    def unknown_ratio(self):
        return self.by_orientation(Orientation.NA)

    def open(self,
             orientation: None | Orientation = None,
             image_type: None | ImageType = None,
             top: None | int = None,
             random: bool = False,
             *,
             path_lst: None | list[str] = None
             ):
        """Open first <top> / all files in default app"""
        
        if orientation is None and image_type is None:
            super().open(top=top, random=random, path_lst=path_lst)
        elif orientation is None and image_type is not None:
            self.by_image_type(image_type)\
                .open(top=top, random=random, path_lst=path_lst)
        elif orientation is not None and image_type is None:
            self.by_orientation(orientation)\
                .open(top=top, random=random, path_lst=path_lst)
        elif orientation is not None and image_type is not None:
            self.by_image_type(image_type)\
                .by_orientation(orientation)\
                .open(top=top, random=random, path_lst=path_lst)
        else:
            raise ValueError('Something wrong with the input')

    def _organize(self, verbose: bool, dry_run: bool):

        for mdate in self.mdates:
            for image_type in ImageType:
                dst_folder = os.path.join(self._target_folder, image_type.value, str(mdate))
                self.by_mdate(mdate)\
                    .by_image_type(image_type)\
                    .move_to(dst_folder, verbose=verbose, dry_run=dry_run)
        
    def _add_file(self, f: ImageFile):
        super()._add_file(f)
        self.orientation_map[f.orientation].append(f)
        self.image_type_map[f.image_type].append(f)

    # TODO - make this accept general arguments (like a few types)
    def by_image_type(self, image_type: ImageType):
        return self.__class__(self.image_type_map[image_type])

    def by_orientation(self, orientation: Orientation):
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
            Orientation.PORT: 1,
            Orientation.LAND: 2,
            Orientation.NA: 3
        }

        for f in self.filelist:
           row = row_map[f.image_type]
           col = col_map[f.orientation]

           summary_table[row][col] += 1
           summary_table[row][-1] += 1
           summary_table[-1][col] += 1
           summary_table[-1][-1] += 1

        print(tabulate(summary_table))

    def _get_details_to_show(self, show_path, color):
        data_dict, total_dict = super()._get_details_to_show(show_path, color)

        data_dict['Height'] = []
        data_dict['Width'] = []
        data_dict['Port/Land'] = []
        data_dict['Image Type'] = []
        for f in self.filelist:
            data_dict['Height'].append(f.height if f.height else "")
            data_dict['Width'].append(f.width if f.width else "")
            data_dict['Port/Land'].append(f.orientation.value)
            data_dict['Image Type'].append(f.image_type.name if f.image_type is not ImageType.NA else "")

        return data_dict, total_dict

class TXTFileList(FileList):

    _category = Category.TXT
    _target_folder = '@document'


class ZIPFileList(FileList):

    _category = Category.ZIP
    _target_folder = '@compressed'
