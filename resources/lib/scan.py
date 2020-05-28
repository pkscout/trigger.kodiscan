
import atexit, argparse, json, os, random, sys, time
import resources.config as config
from resources.lib.xlogger import Logger
from resources.lib.apis import url
from resources.lib.transforms import replaceWords
from resources.lib.fileops import *
from resources.lib.dvrs import *

USEWEBSOCKETS = False
if config.Get( 'use_websockets' ):
    try:
        import websocket
        USEWEBSOCKETS = True
    except ImportError:
        USEWEBSOCKETS = False
if not USEWEBSOCKETS:
    JSONURL = url.URL( 'json', headers={'content-type':'application/json'} )
GENTHUMBS = False
if config.Get( 'gen_thumbs' ):
    try:
        import cv2
        GENTHUMBS = True
    except ImportError:
        GENTHUMBS = False



class Main:
    def __init__( self, thepath ):
        self.ROOTPATH = os.path.dirname( thepath )
        self.PIDFILE = os.path.join( self.ROOTPATH, 'data', 'scan.pid' )
        atexit.register( self._deletePID )
        self.LW = Logger( logfile=os.path.join(self.ROOTPATH, 'data', 'logs', 'logfile.log' ),
                          numbackups=config.Get( 'logbackups' ), logdebug=config.Get( 'debug' ) )
        self._setPID()
        self._parse_argv()
        self._init_vars()
        if not (self.OID and self.DVR):
            self.LW.log( ['do not have OID and DVR config necessary, aborting.'], 'info' )
            return
        if self.FILEPATH:
            if self.TYPE == config.Get( 'tv_dir' ):
                self._fixes()
            self._trigger_scan()
            if config.Get( 'doubletap' ):
                self._trigger_scan()


    def _setPID( self ):
        self.LW.log( ['script started'], 'info' )
        pid = str(os.getpid())
        random.seed()
        time.sleep( random.randint( 1, 10 ) )
        basetime = time.time()
        while os.path.isfile( self.PIDFILE ):
            time.sleep( random.randint( 1, 3 ) )
            if time.time() - basetime > config.Get( 'aborttime' ):
                err_str = 'taking too long for previous process to close - aborting attempt to do scan'
                self.LW.log( [err_str], 'error' )
                sys.exit( err_str )
        self.LW.log( ['setting PID file'] )
        success, loglines = writeFile( pid, self.PIDFILE, wtype='w' )
        self.LW.log( loglines )
        if not success:
            err_str = 'unable to write pid file'
            self.LW.log( [err_str, 'script stopped'], 'error' )
            sys.exit( err_str )


    def _deletePID( self ):
        success, loglines = deleteFile( self.PIDFILE )
        self.LW.log( loglines )
        if not success:
            self.LW.log( ['ubale to delete pid file'] )
        self.LW.log( ['script finished'], 'info' )


    def _parse_argv( self ):
        self.LW.log( ['parsing command line arguments'], 'info' )
        parser = argparse.ArgumentParser()
        parser.add_argument( "theargs", help="the OID of the recording as passed by NPVR", nargs="+" )
        args = parser.parse_args()
        if len( args.theargs ) == 1:
            self.LW.log( ['got %s from command line' % args.theargs[0] ] )
        else:
            self.LW.log( ['got something strange from the command line'] )
            self.LW.log( args.theargs )
            self.LW.log( ['will try and continue with the first argument'] )
        self.OID = args.theargs[0]


    def _init_vars( self ):
        self.LW.log( ['initializing variables'], 'info' )
        self.DVR = self._pick_dvr()
        if not self.DVR:
            self.LW.log( ['invalid DVR configuration, exiting'], 'info' )
            return
        self.ILLEGALCHARS = config.Get( 'illegalchars' )
        self.ILLEGALREPLACE = config.Get( 'illegalreplace' )
        self.ENDREPLACE = config.Get( 'endreplace' )
        self.FIXESDIR = os.path.join( self.ROOTPATH, 'data', 'fixes' )
        exists, loglines = checkPath( os.path.join( self.FIXESDIR, 'default' ) )
        self.LW.log( loglines )
        if not exists:
            self._create_fixes_default( os.path.join( self.FIXESDIR, 'default' ) )
        self.EPISODEINFO, loglines = self.DVR.GetRecordingInfo( self.OID )
        self.LW.log( loglines )
        if not self.EPISODEINFO:
            self.DVR = False
            return
        self.FILEPATH = self.EPISODEINFO['filepath']
        self.FOLDERPATH, filename = os.path.split( self.FILEPATH )
        remainder, self.SHOW = os.path.split( self.FOLDERPATH )
        self.TYPE = os.path.split( remainder )[1]
        kodi_source_root = config.Get( 'kodi_source_root' )
        if kodi_source_root:
            self.KODISOURCE = '%s/%s/%s' % (kodi_source_root, self.TYPE, self.SHOW )
        else:
            self.KODISOURCE = ''
        self.LW.log( ['the filepath is ' + self.FILEPATH, 'the folderpath is ' + self.FOLDERPATH, 'the type is ' + self.TYPE])
        if USEWEBSOCKETS:
            self.KODIURLS = ['ws://%s:%s/jsponrpc' % (config.Get( 'kodiuri' ), config.Get( 'kodiwsport' ) )]
            for remote in config.Get( 'remotekodilist' ):
                self.KODIURLS.append( 'ws://%s:%s/jsponrpc' % (remote.get('kodiuri'), remote.get('kodiwsport', default=config.Get( 'kodiwsport' )) ) )
        else:
            self.KODIURLS = ['http://%s:%s@%s:%s/jsonrpc' % (config.Get( 'kodiuser' ),
                             config.Get( 'kodipass' ),
                             config.Get( 'kodiuri' ),
                             config.Get( 'kodiport' ))]
            for remote in config.Get( 'remotekodilist' ):
                self.KODIURLS.append( 'http://%s:%s@%s:%s/jsonrpc' % (remote.get('kodiuser', default=config.Get( 'kodiuser' )),
                                      remote.get('kodipass', default=config.Get( 'kodipass' )),
                                      remote.get('kodiuri'),
                                      remote.get('kodiport', default=config.Get( 'kodiport' ))) )


    def _create_fixes_default( self, default_fix_dir ):
        default_fix = '<episodedetails>\r' + \
                      '\t<title>[TITLE]</title>\r' + \
                      '\t<season>[SEASON]</season>\r' + \
                      '\t<episode>[EPISODE]</episode>\r' + \
                      '\t<plot>[DESC]</plot>\r' + \
                      '\t<playcount>0</playcount>\r' + \
                      '\t<lastplayed></lastplayed>\r' + \
                      '\t<aired>[AIRDATE]</aired>\r' + \
                      '</episodedetails>\r'
        success, loglines = writeFile( default_fix, os.path.join( default_fix_dir, 'episode.nfo' ), wtype='w' )
        self.LW.log( loglines )


    def _pick_dvr( self ):
        dvr_type = config.Get( 'dvr_type' ).lower()
        if dvr_type == 'nextpvr':
            return nextpvr.DVR( config )
        else:
            return None


    def _fixes( self ):
        self.LW.log( ['creating needed files to import recording into Kodi'], 'info' )
        found_show = False
        try:
            shows = os.listdir( self.FIXESDIR )
        except FileNotFoundError:
            self.LW.log( ['fixes directory does not exist for some reason'], 'error' )
            return
        except Exception as e:
            self.LW.log( ['unknown error getting list of files in fixes directory', e], 'error' )
            return
        self.LW.log( ['there are potential shows to process'], 'info' )
        self.LW.log( shows )
        if self.SHOW.lower() in map( str.lower, shows ):
            self.LW.log( ['matched %s with shows to process' % self.SHOW], 'info' )
            show_fixdir = os.path.join( self.FIXESDIR, self.SHOW )
            found_show = True
        elif "default" in map( str.lower, shows ):
            self.LW.log( ['found default template, applying to %s' % self.SHOW], 'info' )
            show_fixdir = os.path.join( self.FIXESDIR, 'default' )
            found_show = True
        if found_show:
            self._nfofix( os.path.join( show_fixdir, 'episode.nfo') )


    def _nfofix( self, nfotemplate ):
        video_files = []
        other_files = []
        try:
            items = os.listdir( self.FOLDERPATH )
        except OSError:
            err_str = 'directory %s not found' % self.FOLDERPATH
            self.LW.log( [err_str, 'script stopped'], 'error' )
            sys.exit( err_str )
        for item in items:
            fileroot, ext = os.path.splitext( item )
            if ext in config.Get( 'thumb_exts' ):
                for rename_end in config.Get( 'rename_ends' ):
                    if fileroot.endswith( rename_end ):
                        old_thumb = os.path.join( self.FOLDERPATH, item )
                        item = fileroot[:-len( rename_end )] + config.Get( 'thumb_end' ) + ext
                        new_thumb = os.path.join( self.FOLDERPATH, item )
                        success, loglines = renameFile( old_thumb, new_thumb )
                        self.LW.log( loglines )
            if item in config.Get( 'protected_files' ):
                pass
            elif ext in config.Get( 'video_exts' ):
                video_files.append( item )
            else:
                other_files.append( item )
        self._nfo_prune( other_files, video_files )
        if self.EPISODEINFO['season'] == '0':
            self.EPISODEINFO['episode'] = self._special_epnumber( items )
        self._write_nfofile( nfotemplate, os.path.splitext( self.FILEPATH )[0] + '.nfo' )
        self._generate_thumbnail( os.path.join( self.FOLDERPATH, self.FILEPATH ),
                                  os.path.join( self.FOLDERPATH,
                                  os.path.splitext( self.FILEPATH )[0] + '-thumb.jpg' ) )


    def _nfo_prune( self, other_files, video_files ):
        self.LW.log( ['cleaning directory of unneeded files'], 'info' )
        self.LW.log( ['other files:', other_files, 'video files:', video_files] )
        for one_file in other_files:
            match = False
            other_fileroot, throwaway = os.path.splitext( one_file )
            for one_video in video_files:
                video_root, throwaway = os.path.splitext( one_video )
                if (other_fileroot == video_root) or (other_fileroot == video_root + config.Get( 'thumb_end' )):
                    match = True
            if not match:
                success, loglines = deleteFile( os.path.join( self.FOLDERPATH, one_file ) )
                self.LW.log( loglines )


    def _special_epnumber( self, items ):
        ep_num = 1
        for item in items:
            self.LW.log( ['checking file %s' % item] )
            fileroot, ext = os.path.splitext( item )
            if ext == '.nfo':
                self.LW.log( ['file is a nfo file'] )
                loglines, results = readFile( os.path.join( self.FOLDERPATH, item ) )
                self.LW.log( loglines )
                try:
                    season = int( re.findall( '.*<season>(.*)</season>', results )[0] )
                    episode = int( re.findall( '.*<episode>(.*)</episode>', results )[0] )
                except IndexError:
                    season = None
                    episode = 0
                self.LW.log( ['season is %s and episode is %s' %( str( season ), str( episode ) )] )
                if season == 0:
                    self.LW.log( ['nfo file has a 0 season'] )
                    if episode >= ep_num:
                        ep_num = episode + 1
                    self.LW.log( ['epnum is now %s' % str( ep_num )] )
        ep_num = str( ep_num )
        self.LW.log( ['show had no season or episode, setting season to 0 and epsiode to %s' % ep_num], 'info' )
        return ep_num


    def _write_nfofile( self, nfotemplate, newnfoname ):
        self.LW.log( ['writing nfo file'], 'info' )
        newnfopath = os.path.join( self.FOLDERPATH, newnfoname )
        replacement_dic = {
            '[SEASON]': self.EPISODEINFO['season'],
            '[EPISODE]' : self.EPISODEINFO['episode'],
            '[TITLE]' : self.EPISODEINFO['title'],
            '[DESC]' : self.EPISODEINFO['description'],
            '[AIRDATE]' : self.EPISODEINFO["airdate"]}
        exists, loglines = checkPath( newnfopath, createdir=False )
        self.LW.log( loglines )
        if exists:
            success, loglines = deleteFile( newnfopath )
            self.LW.log( loglines )
        loglines, fin = readFile( nfotemplate )
        self.LW.log (loglines )
        if fin:
            newnfo = replaceWords( fin, replacement_dic )
            success, loglines = writeFile( newnfo, newnfopath, wtype='w' )
            self.LW.log( loglines )


    def _generate_thumbnail( self, videopath, thumbpath ):
        if not GENTHUMBS:
            self.LW.log( ['thumbnail generation disabled in settings'], 'info' )
            return
        exists, loglines = checkPath( thumbpath, createdir=False )
        self.LW.log( loglines )
        if exists:
            if self.SHOW not in config.Get( 'force_thumbs' ):
                self.LW.log( ['thumbnail exists and show is not in force_thumbs, skipping thumbnail generation'], 'info' )
                return
            else:
                self.LW.log( ['thumbnail exists but show is in force_thumbs, creating thumbnail'], 'info' )
        else:
            self.LW.log( ['thumb does not exist, creating thumbnail'], 'info' )
        vidcap = cv2.VideoCapture( videopath )
        num_frames = int( vidcap.get( cv2.CAP_PROP_FRAME_COUNT ) )
        fps = int( vidcap.get( cv2.CAP_PROP_FPS ) )
        self.LW.log( ['got numframes: %s and fps: %s' % (str( num_frames ), str( fps ))], 'info' )
        if num_frames < 30 and fps < 30:
            self.LW.log( ['probably an error when reading file with opencv, skipping thumbnail generation'], 'error' )
            return
        if config.Get( 'narrow_time' ):
            custom_narrow = config.Get( 'custom_narrow' )
            try:
                narrow_start = custom_narrow[self.SHOW][0]
                narrow_end = custom_narrow[self.SHOW][1]
            except (KeyError, IndexError):
                narrow_start = config.Get( 'narrow_start' )
                narrow_end = config.Get( 'narrow_end' )
            frame_start = narrow_start*60*fps + config.Get( 'begin_pad_time' )*60*fps
            frame_end = narrow_end*60*fps + config.Get( 'begin_pad_time' )*60*fps
        else:
            frame_start = config.Get( 'begin_pad_time' )*60*fps
            frame_end = num_frames - config.Get( 'end_pad_time' )*60*fps
        random.seed()
        frame_cap = random.randint( frame_start, frame_end )
        self.LW.log( ['capturing frame %s from range %s - %s' % (str( frame_cap ), str( frame_start ), str( frame_end ))], 'info' )
        vidcap.set( cv2.CAP_PROP_POS_FRAMES,frame_cap )
        success, image = vidcap.read()
        if success:
            success, buffer = cv2.imencode(".jpg", image)
            if success:
                success, loglines = writeFile( buffer, thumbpath, wtype='wb' )
                self.LW.log( loglines )
            else:
                self.LW.log( ['unable to encode thumbnail'], 'error' )
        else:
            self.LW.log( ['unable to create thumnail: frame out of range'], 'error' )


    def _trigger_scan( self ):
        self.LW.log( ['triggering Kodi scan'], 'info' )
        jsondict = {}
        jsondict['id'] = '1'
        jsondict['jsonrpc'] = '2.0'
        jsondict['method'] = "VideoLibrary.Scan"
        if self.KODISOURCE == '':
            jsondict['params'] = {"directory":self.FOLDERPATH}
        else:
            jsondict['params'] = {"directory":self.KODISOURCE + '/'}
        jsondata = json.dumps( jsondict )
        time.sleep( config.Get( 'scan_delay' ) )
        if USEWEBSOCKETS:
            self._trigger_via_websocket( jsondata )
        else:
            time.sleep( 20 ) #this is to allow time for a previous scan to finish before starting the next process
            for kodiurl in self.KODIURLS:
                success, loglines, data = JSONURL.Post( kodiurl, data=jsondata )
                self.LW.log( loglines )


    def _trigger_via_websocket( self, jsondata ):
        def on_message(ws, message):
            self.LW.log( ['got back: ' + message] )
            if "VideoLibrary.OnScanFinished" in message:
                self.LW.log( ['got back scan complete message, attempting to close websocket'], 'info' )
                ws.close()
            ws_aborttime = config.Get( 'aborttime' ) - 5
            if time.time() - self.WSTIME > ws_aborttime:
                raise WebSocketException( "process has taken longer than %s seconds - terminating" % str( ws_aborttime ) )
        def on_error(ws, error):
            self.LW.log( [error], 'error' )
            ws.close()
        def on_close(ws):
            self.LW.log( ['websocket connection closed'], 'info' )
        def on_open(ws):
            self.LW.log( ['sending: ' + jsondata] )
            ws.send( jsondata )
        for kodiurl in self.KODIURLS:
            ws = websocket.WebSocketApp( kodiurl, on_message = on_message, on_error = on_error, on_open = on_open, on_close = on_close )
            self.LW.log( ['websocket connection opening'], 'info' )
            self.WSTIME = time.time()
            ws.run_forever()
