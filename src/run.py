
from core.manager import Manager
from core.enums import SortAttr, Category

manager = Manager(
    folder='/media/yaqi/red2/',  # '/mnt/tmp2/',
    recursive=True,
    video_probe_on=True,
    image_probe_on=True,
    # use_cache = {Category.AUDIO: False}
)
# manager.organize(dry_run=False)
# manager.summary()
# manager.save()

# manager.videos.exlongs.open()
