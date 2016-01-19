# xbmc username and password
# set in SYSTEM -> SETTINGS -> SERVICES -> WEBSERVER
xbmcuser = 'xbmc'
xbmcpass = 'xbmc'

# the URL and port XBMC web services are using
# these shouldn't need to change unless you change the port number in XBMC
# set in SYSTEM -> SETTINGS -> SERVICES -> WEBSERVER
xbmcuri = 'localhost'
xbmcport = 8080

# the extensions the script uses for video files
video_exts = {'.ts', '.mp4', '.wmv', '.m4v', '.mkv', '.mpg'}

# the extensions the script uses for thumbnail files
thumb_exts = {'.png', '.jpg'}

# these are thumb endings that need to be renamed to the Kodi standard -thumb
rename_ends = {'-thumbs'}

# these are the extensions of files that should be deleted if no matching video file is found
delete_exts = {'.nfo', '-thumb.jpg', '-thumb.png'}

# the path to the NextPVR database (including the actual database file)
# you shouldn't need to change this unless you have a non-standard NPVR install
db_loc = 'C:\\Users\\Public\\NPVR\\npvr.db3'


