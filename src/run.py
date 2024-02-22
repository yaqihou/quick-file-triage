
from core.manager import Manager
from core.enums import SortAttr, Category

m= Manager(
    folder='/media/yaqi/red2/',  # '/mnt/tmp2/',
    recursive=True,
    probe_on = True,
    use_cache = {Category.AUDIO: False}
)
# manager.organize(dry_run=False)
# manager.summary()
# manager.save()

# manager.videos.exlongs.open()
