defaults = {'dvr_type': 'nextpvr',
            'dvr_host': '127.0.0.1',
            'dvr_port': '8866',
            'dvr_user': '',
            'dvr_auth': '0000',
            'gen_thumbs': True,
            'use_websockets': True,
            'narrow_time': True,
            'narrow_start': 14,
            'narrow_end': 16,
            'custom_narrow': {},
            'comskip_check': True,
            'comskip_padding': 10,
            'tv_dir': 'TVShows',
            'begin_pad_time': 0,
            'end_pad_time': 0,
            'force_thumbs': {''},
            'nas_mount': '',
            'kodi_source_root': '',
            'aborttime': 30,
            'scan_delay': 0,
            'doubletap': False,
            'kodiport': 8080,
            'kodiuser': 'kodi',
            'kodipass': 'kodi',
            'kodiuri': 'localhost',
            'kodiwsport': 9090,
            'remotekodilist': [],
            'video_exts': {'.ts', '.mp4', '.wmv', '.m4v', '.mkv', '.mpg', '.strm', '.disc'},
            'thumb_exts': {'.png', '.jpg'},
            'thumb_end': '-thumb',
            'rename_ends': {'-thumbs'},
            'protected_files': {'tvshow.nfo', 'poster.jpg', 'poster.png',
                                'banner.jpg', 'banner.png', 'fanart.jpg',
                                'fanart.png', 'folder.jpg', 'folder.png'},
            'logbackups': 7,
            'debug': False}


try:
    import data.settings as overrides
    has_overrides = True
except ImportError:
    has_overrides = False


def Reload():
    if has_overrides:
        reload(overrides)


def Get(name):
    setting = None
    if has_overrides:
        setting = getattr(overrides, name, None)
    if not setting:
        setting = defaults.get(name, None)
    return setting
