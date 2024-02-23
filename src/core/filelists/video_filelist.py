import os
from tabulate import tabulate


from .audio_filelist import AudioFileList
from ..enums import Category, MediaLengthType, Orientation
from ..utils import parse_sec_to_str
from ..files import VideoFile


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

        if f.probed and f.broken:
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
        if f.name.startswith(prefix) or not f.probed:
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

        # Remove the unknown col or row if needed
        if summary_table[-2][-1] == 0:  # could remove row
            summary_table = summary_table[:-2] + [summary_table[-1]]

        if summary_table[-1][-2] == 0:  # could remove col
            summary_table = [x[:-2] + [x[-1]] for x in summary_table]

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

