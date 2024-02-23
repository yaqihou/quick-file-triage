#!/usr/bin/python3

import abc
import os
import pickle
from tqdm import tqdm
import datetime as dt

from termcolor import colored

from .utils import need_confirm
from .enums import Category
from .filelists import AudioFileList, VideoFileList, DocFileList, CompressedFileList
from .filelists import ImageFileList, FileList


CACHE_PKL = os.path.join(os.environ['HOME'], '.cache', 'my-file-organizer', 'cache.pkl')

# TODO - the probe could be put into a later stage (after creating the file list)
# TODO - refactor the cache: save all data in native data structure
# TODO - add fast mode, i.e. don't walk through the real filelist but using the cached dict, and could check if existed in lazily
# TODO - the chdir thing limit one feature: for example, we may want to add files interactively from a different directory, need to comb through the logic here
# TODO - move cache to be "base-folder" based so that it could work for multiple projects

# TODO - create a base Manager to support multiple-purpose reuse


class ManagerBase(abc.ABC):

    cache_all: dict[str, dict] = {}
    if os.path.isfile(CACHE_PKL):
        with open(CACHE_PKL, 'rb') as f:
            cache_all = pickle.load(f)
            print(f'Found cache for {len(cache_all)} locations')
            for k, v in cache_all.items():
                print(f'    - {k} ({len(v)} entries)')

    @property
    def cache(self) -> dict[str, dict]:
        return self.cache_all.get(self.cwd, {})

    def save_cache(self):
        """Save file list, the path is used as key"""
        _dict = {}
        for fl in self.data.values():
            _dict.update(fl.to_dict())

        self._check_conflicting_cache(_dict)
        self.cache.update(_dict)
        self.cache_all[self.cwd] = self.cache

        folder = os.path.dirname(CACHE_PKL)
        os.makedirs(folder, exist_ok=True)
        with open(CACHE_PKL, 'wb') as f:
            pickle.dump(self.cache_all, f)

        print(f'File cache saved successfully!')

    @need_confirm('Do you want to save cache?')
    def save_cache_with_confirm(self):
        return self.save_cache()

    def _check_conflicting_cache(self, _dict):

        dup_confirm = False
        conflict_keys = []
        dup_keys = _dict.keys() & self.cache.keys()
        for key in dup_keys:
            if _dict[key] != self.cache[key]:
                dup_confirm = True
                conflict_keys.append(key)

        if dup_confirm:
            print(f"Found conflicting cache keys:")
            for key in conflict_keys:
                print(' ' * 4 + f'+ {key}')

                for kk in _dict[key].keys() | self.cache[key].keys():
                    oldv = self.cache[key].get(kk, "")
                    newv = _dict[key].get(kk, "")
                    print(' ' * 8 + f'{kk}: {oldv} -> {newv}')
                    
    # ----------------------------------
    def __init__(self, folder: str,
                 *,
                 recursive: bool = False,
                 auto_probe: bool | dict[Category, bool] = False,
                 use_cache: bool | dict[Category, bool] = True,
                 managed_data: dict[Category, FileList] | None = None):

        folder = os.path.abspath(folder)
        os.chdir(folder)
        self.cwd = folder

        self.use_cache = use_cache
        self.auto_probe = auto_probe

        if managed_data is None:
            self.data = self._init_data()
            self._load(recursive=recursive)
        else:
            self.data = managed_data

    def __getitem__(self, cat: Category):
        """Aliast to by_cat"""
        return self.by_cat(cat)

    def __len__(self):
        return sum(len(val) for val in self.data.values())

    @property
    def len(self):
        return self.__len__()

    @abc.abstractmethod
    def _init_data(self) -> dict:
        """Return the empty data dictionary"""

    def _load(self, recursive: bool = False):
        """Load the initial folder content"""

        # We only use this function internally so that the cwd is already set
        pathlist = self._prepare_pathlist('.', recursive=recursive)
        
        for path in tqdm(pathlist, desc="Loading files"):
            cat = Category.infer(os.path.basename(path))

            use_cache = (self.use_cache if isinstance(self.use_cache, bool)
                          else self.use_cache.get(cat, True))

            if not use_cache or path not in self.cache:
                self._add_file(path, cat)
            else:
                self._add_file_from_cache(self.cache[path], cat)
        return 
 
    def _prepare_pathlist(self, base_folder: str, recursive: bool = False):
        """Return a list of file paths (relative) under the given base_folder path"""
     
        base_folder = os.path.relpath(base_folder, '.')

        # Note that we assume the working directory has been changed already
        if not recursive:
            pathlist = list(filter(
                os.path.isfile,
                (os.path.join(base_folder, f) for f in os.listdir(base_folder))
            ))
        else:
            pathlist = []
            for (root, dirs, files) in os.walk(base_folder, topdown=True):
                root = os.path.relpath(root, base_folder)

                # Prune the dirs
                dirs[:] = [d for d in dirs if not self._exclude_folder(d)]
                if root == '.':  # if root is current
                    pathlist += files
                else:
                    assert not (root.startswith('#') and root.startswith('.'))
                    pathlist += [os.path.join(root, f) for f in files]

        return pathlist

    def _exclude_folder(self, d: str):
        if d[0] == '#':  return True
        elif len(d) > 1 and d[0] == '.':  return True

        return False

    def _add_file(self, path_or_file, cat):
        auto_probe = (
            self.auto_probe if isinstance(self.auto_probe, bool)
            else self.auto_probe.get(cat, True))

        self.data[cat].add_file(path_or_file, auto_probe=auto_probe)

    def _add_file_from_cache(self, cache_dict, cat):
        self.data[cat].add_file_from_cache(cache_dict)

    def add_file(self, path: str):
        cat = Category.infer(os.path.basename(path))
        return self._add_file(path, cat)

    def add_folder(self, path: str, recursive: bool = False):
        if not os.path.isdir(path):
            print(f'Given path {path} is not a folder')
            return

        pathlist = self._prepare_pathlist(path, recursive=recursive)
        for path in tqdm(pathlist, desc=f"Adding folder"):
            self.add_file(path)

    # ----------------------------------
    def _by(self, key:  Category | dt.date, target: dict):
        if key in target:
            return FileList(filelist=target[key])
        else:
            raise ValueError(f"There are no files in given key: {key}")

    def by_cat(self, cat: Category):
        return self.data[cat]

    def by_mdate(self, date: dt.date):
        return self.__class__(
            self.cwd,
            managed_data={
                key: val.by_mdate(date) for key, val in self.data.items()
            })

    def by_folder(self, folder_prefix):
        return self.__class__(
            self.cwd,
            managed_data={
                key: val.by_folder(folder_prefix) for key, val in self.data.items()
            })

    @property
    def mdates(self):
        ret = []
        for fl in self.data.values():
            ret += fl.mdates
        return list(sorted(ret))

    @property
    def folders(self):
        _dict = {}
        for fl in self.data.values():
            _dict.update(fl.folders)

        return _dict

    # ----------------------------------
    # Dates related alias
    
    # ----------------------------------
    # Filesize related alias
    def large_files(self):
        pass

    def small_files(self):
        pass

    # ----------------------------------
    def probe(self, force: bool = False, verbose: bool = False):
        for fl in self.data.values():
            fl.probe(force=force, verbose=verbose)
    
    @property
    def probed(self):
        return self.__class__(
            self.cwd,
            managed_data={
                key: val.probed for key, val in self.data.items()
            })

    @property
    def unprobed(self):
        return self.__class__(
            self.cwd,
            managed_data={
                key: val.unprobed for key, val in self.data.items()
            })

    # ----------------------------------
    def organize(self, verbose=False, dry_run=False):
        if dry_run:
            self._organize(verbose=verbose, dry_run=dry_run)
        else:
            self._organize_with_confirm(verbose=verbose, dry_run=dry_run)

    def _organize(self, verbose=False, dry_run=False):
        for fl in self.data.values():
            fl.organize(verbose=verbose, dry_run=dry_run)

        if not dry_run:
            self.save_cache_with_confirm()

    @need_confirm('Are you sure to organize all files automatically?')
    def _organize_with_confirm(self, verbose=False, dry_run=False):
        return self._organize(verbose=verbose, dry_run=False)

    @need_confirm('Are you sure to move all files to a single folder?')
    def move_all_to(self, dst_folder, verbose=True, dry_run=False):
        for fl in self.data.values():
            fl.move_to(dst_folder, verbose=verbose, dry_run=dry_run)

        if not dry_run:
            self.save_cache_with_confirm()

    # ----------------------------------
    def summary(self, cat: Category | None = None):
        if cat is None:
            _tot_len = 0
            for fl in self.data.values():
                fl.summary()
                _tot_len += len(fl)
            print('---------------')
            print(f"Total file counts: {_tot_len}")
        else:
            self.data[cat].summary()


class Manager(ManagerBase):

    def _init_data(self):
        return {
            Category.VIDEO: VideoFileList(),
            Category.IMAGE: ImageFileList(),
            Category.AUDIO: AudioFileList(),
            Category.TXT: DocFileList(),
            Category.ZIP: CompressedFileList(),
            Category.NA: FileList()
        }

    # Category alias
    @property
    def videos(self):
        return self.by_cat(Category.VIDEO)

    @property
    def images(self):
        return self.by_cat(Category.IMAGE)

    @property
    def audios(self):
        return self.by_cat(Category.AUDIO)

    @property
    def docs(self):
        return self.by_cat(Category.TXT)

    @property
    def zips(self):
        return self.by_cat(Category.ZIP)

    @property
    def other(self):
        return self.by_cat(Category.NA)

    def play_all_video(self, random=False):
        self.data[Category.VIDEO].open(random=random)

    def play_all_image(self, random=False):
        self.data[Category.IMAGE].open(random=random)

