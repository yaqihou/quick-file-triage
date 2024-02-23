
from termcolor import colored

from core.manager import Manager
from core.enums import SortAttr, Category
import argparse 

parser = argparse.ArgumentParser()
parser.add_argument('folder', default='', nargs=1)
parser.add_argument('-r', '--recursive', action='store_true')
args = parser.parse_args()

folder = args.folder[0]
print('Changing current working directory to', colored(folder, 'green'))
m= Manager(
    folder=folder,
    recursive=args.recursive,
    auto_probe = False,
)
# manager.organize(dry_run=False)
# manager.summary()
# manager.save()

# manager.videos.exlongs.open()
