
import os
import abc
from random import shuffle
import datetime as dt
from tqdm import tqdm
from termcolor import colored
import subprocess as sp
from tabulate import SEPARATING_LINE, tabulate

from ..enums import Category, SortAttr
from ..files import File
from ..utils import MinType, get_readable_filesize 

# TODO - support general query search
# TODO - add random play support for open
# TODO - the popen needs re-work, it doesn't has any use in its current stage

class FileList(abc.ABC):

    _category: Category = Category.NA
    _open_file_cmd_lst: list[str] = []
    _target_folder = '.'
    _file_type: type = File

    _large_file_lower_bound = 5 * 1024 * 1024  # 5M
    _small_file_upper_bound = 5 * 1024 ** 3  # 1G

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

    def _path_iter(self):
        for f in self.filelist:
            yield f.path

    def __del__(self):
        FileList.process_list = [p for p in FileList.process_list if p.poll() is None]

    def __len__(self):
        return len(self.filelist)

    @property
    def len(self):
        return self.__len__()

    # ----------------------------------
    def add_file(self,
                 path_or_file: str | File,
                 auto_probe: bool = False,
                 **kwargs):

        if isinstance(path_or_file, str):
            if os.path.isfile(path_or_file):
                f = self._file_type(path_or_file, auto_probe=auto_probe)
            else:
                raise ValueError(f"Given path {path_or_file} doesn't exist")

        elif isinstance(path_or_file, File):
            f = path_or_file

        else:
            raise ValueError(f'Given input {path_or_file} should be a path str or File instance')

        self._add_file(f)

    def probe(self, force: bool = False, verbose: bool = False):
        _iter = (tqdm(self.filelist,
                      desc=f'[{self.category}] Probing metadata')
                 if not verbose else self.filelist
                 )

        for f in _iter:
            f.probe(force=force, verbose=verbose)

    @property
    def unprobed(self):
        return self.__class__(filelist=[f for f in self.filelist if not f.probed])

    @property
    def probed(self):
        return self.__class__(filelist=[f for f in self.filelist if f.probed])

    def add_file_from_cache(self, _dict):
        self._add_file(self._file_type.from_dict(_dict))

    # ----------------------------------
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

    # ----------------------------------
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

    # ----------------------------------
    # Size related methods
    
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
        _lst = list(self._path_iter())[:top]
        if random:  shuffle(_lst)
        return _lst

    # File move / organize related methods

    def _get_dst(self, f: File, dst_folder: str):
        return os.path.join(dst_folder, f.name)

    def organize(self, verbose: bool = False, dry_run: bool = False):
        if self._target_folder is None:
            print("No target folder defined to organize the file into")
        else:
            self._organize(verbose, dry_run)

    def _organize(self, verbose: bool = False, dry_run: bool = False):
        """Default organize behaviour"""

        dst_folder = self._target_folder
        self.move_to(dst_folder, verbose=verbose, dry_run=dry_run)

    @staticmethod
    def _prepare_dir(folder):
        if not os.path.exists(folder):
            print(f'Destination folder {colored(folder, "green")} does not exist, creating it now...')
            os.makedirs(folder)

    def move_to(self, dst_folder: str, verbose: bool = True, dry_run: bool = False):
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
                print(f'   - [{f.size_human}] {f.path}')
                print(f'   + [{f.size_human}] {dst}')

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

            data_dict['Size'].append(
                f.size_human if not color else colored(f.size_human, 'yellow')
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



