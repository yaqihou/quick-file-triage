
from .filelist import FileList
from ..enums import Category

class CompressedFileList(FileList):

    _category = Category.ZIP
    _target_folder = '@compressed'
