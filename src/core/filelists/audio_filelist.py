import os
from tabulate import tabulate


from .filelist import FileList
from ..enums import Category, MediaLengthType
from ..utils import parse_sec_to_str
from ..files import AudioFile

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

        if f.probed and f.broken:
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

