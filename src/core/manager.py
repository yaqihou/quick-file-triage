#!/usr/bin/python3

# TODO - Add GUI / interface

import os
import pickle
from tqdm import tqdm
import datetime as dt

from termcolor import colored

from .utils import need_confirm
from .enums import Category
from .files import File, FileFactory, VideoFile, ImageFile
from .filelist import VideoFileList, ImageFileList, AudioFileList, TXTFileList, ZIPFileList, FileList

CACHE_PKL = os.path.join(os.environ['HOME'], '.cache', 'my-file-organizer', 'cache.pkl')

# TODO - the probe could be put into a later stage (after creating the file list)
# TODO - refactor the cache: save all data in native data structure
# TODO - add fast mode, i.e. don't walk through the real filelist but using the cached dict, and could check if existed in lazily

class Manager():

    cache: dict[str, File] = {}
    if os.path.isfile(CACHE_PKL):
        with open(CACHE_PKL, 'rb') as f:
            cache = pickle.load(f)
            print(f'Loaded {len(cache)} cached entries')

    def __init__(self, *,
                 folder: str | None = None,
                 recursive: bool = False,
                 probe_on: bool | dict[Category, bool] = True,
                 use_cache: bool | dict[Category, bool] = True,
                 managed_data: dict[Category, FileList] | None = None):

        if folder is not None and managed_data is not None:
            print('Both folder and managed_data is set, use managed_data by default')
            folder = None

        if folder is None and managed_data is None:
            raise ValueError('Pleaes give at least a folder or managed_data')

        assert folder is not None
        folder = os.path.abspath(folder)
        os.chdir(folder)
        print('Chaning current working directory to', colored(folder, 'green'))

        self.use_cache = use_cache
        self.probe_on = probe_on

        if managed_data is None:
            self.data = {
                Category.VIDEO: VideoFileList(),
                Category.IMAGE: ImageFileList(),
                Category.AUDIO: AudioFileList(),
                Category.TXT: TXTFileList(),
                Category.ZIP: ZIPFileList(),
                Category.NA: FileList()
            }
            self.load(recursive=recursive)
        else:
            self.data = managed_data

    def __getitem__(self, cat: Category):
        """Aliast to by_cat"""
        return self.by_cat(cat)

    # Bunck of alias
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

    def _by(self, key:  Category | dt.date, target: dict):
        if key in target:
            return FileList(filelist=target[key])
        else:
            raise ValueError(f"There are no files in given key: {key}")

    def by_cat(self, cat: Category):
        return self.data[cat]

    def by_mdate(self, date: dt.date):
        return Manager(
            managed_data={
                key: val.by_mdate(date) for key, val in self.data.items()
            })

    @need_confirm('Are you sure to organize all files automatically?')
    def organize(self, verbose=True, dry_run=False):
        for fl in self.data.values():
            fl.organize(verbose=verbose, dry_run=dry_run)

        if not dry_run:
            self.save_cache()

    @need_confirm('Are you sure to move all files to a single folder?')
    def move_all_to(self, dst_folder, verbose=True, dry_run=False):
        for fl in self.data.values():
            fl.move_to(dst_folder, verbose=True, dry_run=False)

        if not dry_run:
            self.save_cache()

    @property
    def mdates(self):
        ret = []
        for fl in self.data.values():
            ret += fl.mdates
        return list(sorted(ret))

    def summary(self, cat: Category | None = None, compact=True):
        if cat is None:
            _tot_len = 0
            for fl in self.data.values():
                fl.summary()
                if not compact:
                    fl.details()
                _tot_len += len(fl)
            print('---------------')
            print(f"Total file counts: {_tot_len}")
        else:
            self.data[cat].summary()

    def _to_namelist(self, filelist: list[File]) -> list[str]:
        return [f.name for f in filelist]

    def play_all_video(self, random=False):
        self.data[Category.VIDEO].open(random=random)

    def play_all_image(self, random=False):
        self.data[Category.IMAGE].open(random=random)
            
    def load(self, recursive=False):

        # Note that we assume the working directory has been changed already
        if not recursive:
            pathlist = [f for f in os.listdir('.')]
            pathlist = list(filter(os.path.isfile, pathlist))
        else:
            pathlist = []
            for (root, dirs, files) in os.walk('.', topdown=True):
                root = os.path.relpath(root, '.')

                # Prune the dirs
                dirs[:] = [d for d in dirs if not (d.startswith('#') or d.startswith('.'))]
                if root == '.':  # root is current
                    pathlist += files
                else:
                    assert not (root.startswith('#') and root.startswith('.'))
                    pathlist += [os.path.join(root, f) for f in files]
        
        for path in tqdm(pathlist, desc="Loading files"):
            cat = Category.infer(os.path.basename(path))

            use_cache = (self.use_cache if isinstance(self.use_cache, bool)
                          else self.use_cache.get(cat, True))

            if not use_cache or path not in self.cache:
                print('Loading from path now', path)
                self.add_file(path, cat)
            else:
                self.add_file_from_cache(self.cache[path], cat)
        return 

    def add_file(self, path_or_file, cat):
        probe_on = (self.probe_on if isinstance(self.probe_on, bool)
                    else self.probe_on.get(cat, True))
        self.data[cat].add_file(path_or_file, probe_on=probe_on)

    def add_file_from_cache(self, cache_dict, cat):
        self.data[cat].add_file_from_cache(cache_dict)

    def save_cache(self):
        """Save file list, the path is used as key"""
        _dict = {}
        for fl in self.data.values():
            _dict.update(fl.to_dict())

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
                print(f'    - {key}')
             
        self.cache.update(_dict)

        folder = os.path.dirname(CACHE_PKL)
        os.makedirs(folder, exist_ok=True)
        with open(CACHE_PKL, 'wb') as f:
            pickle.dump(self.cache, f)

        print(f'File cache saved successfully!')

