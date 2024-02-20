#!/usr/bin/python3

# TODO - Add random play
# TODO - Add GUI / interface

import os
import pickle
from tqdm import tqdm
import datetime as dt

from termcolor import colored

from .utils import need_confirm
from .enums import Category
from .files import File, VideoFile, ImageFile
from .filelist import VideoFileList, ImageFileList, AudioFileList, TXTFileList, ZIPFileList, FileList

CACHE_PKL = os.path.join(os.environ['HOME'], '.cache', 'my-file-organizer', 'cache.pkl')

class Manager():

    cache: dict[str, File] = {}
    if os.path.isfile(CACHE_PKL):
        with open(CACHE_PKL, 'rb') as f:
            cache = pickle.load(f)

    def __init__(self, *,
                 folder: str | None = None,
                 recursive: bool = False,
                 video_probe_on: bool = True,
                 image_probe_on: bool = True,
                 use_cache: bool = True,
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
        
        if managed_data is None:
            filelist = self.load(
                video_probe_on=video_probe_on,
                image_probe_on=image_probe_on,
                recursive=recursive,
                use_cache=use_cache)
            self.data = {
                Category.VIDEO: VideoFileList(),
                Category.IMAGE: ImageFileList(),
                Category.AUDIO: AudioFileList(),
                Category.TXT: TXTFileList(),
                Category.ZIP: ZIPFileList(),
                Category.NA: FileList()
            }

            for f in filelist:
                self.data[f.cat].add_file(f)
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

    @need_confirm('Are you sure to move all files to a single folder?')
    def move_all_to(self, dst_folder, verbose=True, dry_run=False):
        for fl in self.data.values():
            fl.move_to(dst_folder, verbose=True, dry_run=False)

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

    def play_all_video(self):
        self.data[Category.VIDEO].open()

    def play_all_image(self):
        self.data[Category.IMAGE].open()
            
    def load(self, video_probe_on=True, image_probe_on=True, recursive=False, use_cache=True):

        # Note that we assume the working directory has been changed already
        if not recursive:
            pathlist = [f for f in os.listdir('.')]
            pathlist = list(filter(os.path.isfile, pathlist))
        else:
            pathlist = []
            for (root, _, files) in os.walk('.'):
                root = os.path.relpath(root, '.')
                if root.startswith('#') or root.startswith('.'):
                    continue
                else:
                    pathlist += [os.path.join(root, f) for f in files]
        
        ret = []
        for path in tqdm(pathlist, desc="Loading files"):
            cat = Category.infer(os.path.basename(path))

            if not use_cache or path not in self.cache:
                # TODO - use the interface from FileList class
                if cat == Category.VIDEO:
                    ret.append(VideoFile(path, probe_on=video_probe_on))
                elif cat == Category.IMAGE: 
                    ret.append(ImageFile(path, probe_on=image_probe_on))
                else:
                    ret.append(File(path))
            else:
                ret.append(self.cache[path])
        return ret

    def save(self):
        """Save file list, the path is used as key"""
        _dict = {}
        for fl in self.data.values():
            _dict.update(fl.to_dict())
        self.cache = _dict

        folder = os.path.dirname(CACHE_PKL)
        os.makedirs(folder, exist_ok=True)
        with open(CACHE_PKL, 'wb') as f:
            pickle.dump(self.cache, f)

        print(f'File cache saved successfully!')

