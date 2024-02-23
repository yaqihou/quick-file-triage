
import os
import shutil
import datetime as dt
from termcolor import colored

from ..utils import get_readable_filesize

from ..enums import Category, Enum

# TODO - modify the anime_or_not to support 4-channel (alpha) PNG files

class File():

    def __init__(
            self,
            path: str,
            *,
            auto_probe: bool = False,
            preassigned_attrs = {}
    ):

        self.path: str = path
        self.probed: bool = False

        self.name: str = ""
        self.cat: Category = Category.NA

        self.fstat: dict = {}

        if not preassigned_attrs:
            self._probe_base_info()
            if auto_probe:  self._probe()
        else:
            for attr, val in preassigned_attrs.items():
                # NOTE - Let it crash if the attr not defined
                default_attr = getattr(self, attr)
                setattr(self, attr,
                        type(default_attr)[val] if isinstance(default_attr, Enum) else val)


    @property
    def mtime(self):
        return self.fstat['st_mtime']

    @property
    def mdate(self):
        return self.mtime.date()

    @property
    def size(self):
        return self.fstat['st_size']

    @property
    def size_human(self):
        return get_readable_filesize(self.fstat['st_size'])
    
    def _probe_base_info(self):

        self.name: str = os.path.basename(self.path)
        self.cat: Category = Category.infer(self.name)

        # save as dict to allow parsing
        _fstat = os.stat(self.path)
        self.fstat = {attr: getattr(_fstat, attr) for attr in dir(_fstat) if attr.startswith('st_')}

        for k, v in self.fstat.items():
            if k.endswith('time'):
                self.fstat[k] = dt.datetime.fromtimestamp(v)
            elif k.endswith('time_ns'):
                self.fstat[k] = dt.datetime.fromtimestamp(v // 1_000_000_000)

    def _probe(self):
        """Populate other meta info fields"""
        return

    def probe(self, force: bool = False, verbose: bool = False):
        if force or not self.probed:
            if verbose:  print(f'Probing for file {self.name}')
            self._probe()
    
    def update_path(self, new_path):
        self.path = new_path

    def move(self, dst, verbose=False, dry_run=False):
        if dry_run:
            print(f'Will move {colored(self.path, "yellow")}\n    -> {colored(dst, "green")}')

        if not dry_run:
            if verbose:
                print(f'Moving {self.path} -> {dst}')
            shutil.move(self.path, dst)
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
        other_fields = {k: v for k, v in prop_dict.items()
                        if k not in ['path']}
        return cls(path, preassigned_attrs=other_fields)


