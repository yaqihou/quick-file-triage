
from core.manager import Manager

manager = Manager(
    folder= '/mnt/tmp2/',
    recursive=True,
    video_probe_on=True,
    image_probe_on=True)
# manager.organize(dry_run=True)
manager.summary()
# manager.save()

# manager.images.open(top=200)
