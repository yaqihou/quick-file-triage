
def need_confirm(msg="Need confirm to continue"):
    def decorator(func):
        def wrapped(*args, **kwargs):
            _in = input(msg + ' [Y/n] ')
            if _in.upper() == 'N':
                pass
            elif _in.upper() in ('Y', ''):
                return func(*args, **kwargs)

        return wrapped

    return decorator

def get_readable_filesize(fsize):
    
    try:
        idx = 0
        while fsize > 1024:
            idx += 1
            fsize /= 1024

        unit = ['B', 'KB', 'MB', 'GB', 'TB'][idx]
    except:
        return '#N/A'
    else:
        return f"{fsize:6.2f} {unit}"
