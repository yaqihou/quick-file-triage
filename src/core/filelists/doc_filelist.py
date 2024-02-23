
from .filelist import FileList
from ..enums import Category

class DocFileList(FileList):

    _category = Category.TXT
    _target_folder = '@document'
