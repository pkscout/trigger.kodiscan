# if you want to turn off generation of missing thumbnails, set to False
# requires cv2 module to be present (see readme for instructions)
gen_thumbs = True

# if you want to use HTTP to send commands to Kodi instead of websockets, set to False
# requires websocket-client module to be present (see readme for instructions)
use_websockets = True

# set to False if you want the script to select a frame from the entire file instead of
# a the narrow window of about 5 minutes near the beginning that, in the US, is almost
# always the actual show
narrow_time = True

# the system assumes you have split TV shows and movies into separate sections
# you need to provide the directory names here
# these should be the same in the local NPVR recording directory and the remote NAS location
movie_dir = 'Movies'
tv_dir = 'TVShows'

# indicate how much you pad your recordings at the beginning and end (in minutes)
begin_pad_time = 0
end_pad_time = 0

# shows that should generate thumbs even if they exist already
force_thumbs = {''}

# if you want to move your files to an external NAS, set the root location here
# nas_mount is the local mount point definition like 'Z:/Media/Kodi'
nas_mount = ''

# if you're using SMB for you Kodi sources, you need to list it here to trigger the library scan
# smb_name is the SMB name in Kodi like 'smb://htpc/Media/Kodi'
# don't include the final directory for the TV Shows or Movies
smb_name = ''

#if another instance of script is running, amount of time to wait before giving up
aborttime = 30

# port, username, and password set in SYSTEM -> SETTINGS -> SERVICES -> WEBSERVER
# none of these are used if your using the websocket connection
kodiport = 8080
kodiuser = 'kodi'
kodipass = 'kodi'

# the URL Kodi remote command services are using
kodiuri = 'localhost'

# the port for websocket
kodiwsport = 9090

# the extensions the script uses for video files
video_exts = {'.ts', '.mp4', '.wmv', '.m4v', '.mkv', '.mpg'}

# the extensions the script uses for thumbnail files
thumb_exts = {'.png', '.jpg'}

# this is what should be at the end of a filename to designate as a thumbnail
thumb_end = '-thumb'

# these are thumb endings that need to be renamed to the setting above
rename_ends = {'-thumbs'}

# these are files that should never be deleted
protected_files = {'tvshow.nfo', 'poster.jpg', 'poster.png', 'banner.jpg', 'banner.png', 'fanart.jpg', 'fanart.png', 'folder.jpg', 'folder.png'}

# the path to the NextPVR database (including the actual database file)
# you shouldn't need to change this unless you have a non-standard NPVR install
db_loc = 'C:\\Users\\Public\\NPVR\\npvr.db3'

# frames per second fallback (only used if opencv can't figure it out from the video
fallback_fps = 30

