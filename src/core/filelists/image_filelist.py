import os
from tabulate import tabulate


from .filelist import FileList
from ..enums import Category, ImageType, Orientation
from ..files import ImageFile

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
