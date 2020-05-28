# v.1.1.7

import atexit, argparse, json, os, random, sys, time, xmltodict
import resources.config as config
from resources.lib.xlogger import Logger
from resources.lib.apis import url
from resources.lib.transforms import replaceWords
from resources.lib.fileops import *
from resources.lib.dvrs import *

lw = Logger( logfile=os.path.join( 'data', 'logs', 'logfile.log' ),
             numbackups=config.Get( 'logbackups' ), logdebug=config.Get( 'debug' ) )

if config.Get( 'use_websockets' ):
    try:
        import websocket
        use_websockets = True
    except ImportError:
        lw.log( ['websocket-client not installed, falling back to JSON over HTTP'] )
        use_websockets = False
if not use_websockets:
    JSONURL = url.URL( 'json', headers={'content-type':'application/json'} )
if config.Get( 'gen_thumbs' ):
    try:
        import cv2
        gen_thumbs = True
    except ImportError:
        lw.log( ['cv2 not installed, disabling thumb generation'] )
        gen_thumbs = False

def _deletePID():
    success, loglines = deleteFile( pidfile )
    lw.log (loglines )
    lw.log( ['script finished'], 'info' )

pid = str(os.getpid())
pidfile = os.path.join( 'data', 'scan.pid' )
atexit.register( _deletePID )


class Main:
    def __init__( self ):
        self._setPID()
        lw.log( ['script started'], 'info' )
        self._parse_argv()
        self._init_vars()
        if not (self.OID and self.DVR):
           return
        if self.FILEPATH:
            if self.TYPE == config.Get( 'tv_dir' ):
                self._fixes()
            self._trigger_scan()
            if config.Get( 'doubletap' ):
                self._trigger_scan()


    def _setPID( self ):
        random.seed()
        time.sleep( random.randint( 1, 10 ) )
        basetime = time.time()
        while os.path.isfile( pidfile ):
            time.sleep( random.randint( 1, 3 ) )
            if time.time() - basetime > config.Get( 'aborttime' ):
                err_str = 'taking too long for previous process to close - aborting attempt to do scan'
                lw.log( [err_str] )
                sys.exit( err_str )
        lw.log( ['setting PID file'] )
        success, loglines = writeFile( pid, pidfile, wtype='w' )
        lw.log( loglines )


    def _parse_argv( self ):
        parser = argparse.ArgumentParser()
        parser.add_argument( "theargs", help="the OID of the recording as passed by NPVR", nargs="+" )
        args = parser.parse_args()
        if len( args.theargs ) == 1:
            lw.log( ['got %s from command line' % args.theargs[0] ] )
        else:
            lw.log( ['got something strange from the command line'] )
            lw.log( args.theargs )
            lw.log( ['will try and continue with the first argument'] )
        self.OID = args.theargs[0]


    def _init_vars( self ):
        self.DVR = self._pick_dvr()
        if not self.DVR:
            lw.log( ['invalid DVR configuration, exiting'] )
            return
        self.ILLEGALCHARS = config.Get( 'illegalchars' )
        self.ILLEGALREPLACE = config.Get( 'illegalreplace' )
        self.ENDREPLACE = config.Get( 'ednreplace' )
        self.FIXESDIR = os.path.join( 'data', 'fixes' )
        exists, loglines = checkPath( os.path.join( self.FIXESDIR, 'default' ) )
        lw.log( loglines )
        if not exists:
            self._create_fixes_default( os.path.join( self.FIXESDIR, 'default' ) )
        self.EPISODEINFO, loglines = self.DVR.GetRecordingInfo( self.OID )
        lw.log( loglines )
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
        lw.log( ['the filepath is ' + self.FILEPATH, 'the folderpath is ' + self.FOLDERPATH, 'the type is ' + self.TYPE])
        if use_websockets:
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
        lw.log( loglines )


    def _pick_dvr( self ):
        dvr_type = config.Get( 'dvr_type' ).lower()
        if dvr_type == 'nextpvr':
            return nextpvr.DVR( config )
        else:
            return None


    def _fixes( self ):
        found_show = False
        try:
            shows = os.listdir( self.FIXESDIR )
        except FileNotFoundError:
            lw.log( ['fixes directory does not exist for some reason'] )
            return
        except Exception as e:
            lw.log( ['unknown error getting list of files in fixes directory', e] )
            return
        lw.log( ['there are potential shows to fix'] )
        lw.log( shows )
        if self.SHOW.lower() in map( str.lower, shows ):
            lw.log( ['matched %s with shows to fix' % self.SHOW] )
            show_fixdir = os.path.join( self.FIXESDIR, self.SHOW )
            found_show = True
        elif "default" in map( str.lower, shows ):
            lw.log( ['found default fix, applying to %s' % self.SHOW] )
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
            lw.log( [err_str, 'script stopped'] )
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
                        lw.log( loglines )
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
        lw.log( ['checking files to see if they need to be deleted'] )
        lw.log( ['other files:', other_files, 'video files:', video_files] )
        for one_file in other_files:
            match = False
            other_fileroot, throwaway = os.path.splitext( one_file )
            for one_video in video_files:
                video_root, throwaway = os.path.splitext( one_video )
                if (other_fileroot == video_root) or (other_fileroot == video_root + config.Get( 'thumb_end' )):
                    match = True
            if not match:
                success, loglines = deleteFile( os.path.join( self.FOLDERPATH, one_file ) )
                lw.log( loglines )


    def _special_epnumber( self, items ):
        ep_num = 1
        for item in items:
            fileroot, ext = os.path.splitext( item )
            if ext == '.nfo':
                loglines, results = readFile( os.path.join( self.FOLDERPATH, item ) )
                lw.log( loglines )
                result_dict = xmltodict.parse( results )
                if result_dict.get( 'season' ) == 0:
                    result_epnum = result_dict.get( 'epsiode', 0 )
                    if result_epnum > ep_num:
                        ep_num = result_epnum
        ep_num = str( ep_num )
        lw.log( ['the episode number calculated for the special season is %s' % ep_num] )
        return ep_num


    def _write_nfofile( self, nfotemplate, newnfoname ):
        newnfopath = os.path.join( self.FOLDERPATH, newnfoname )
        replacement_dic = {
            '[SEASON]': self.EPISODEINFO['season'],
            '[EPISODE]' : self.EPISODEINFO['episode'],
            '[TITLE]' : self.EPISODEINFO['title'],
            '[DESC]' : self.EPISODEINFO['description'],
            '[AIRDATE]' : self.EPISODEINFO["airdate"]}
        exists, loglines = checkPath( newnfopath, createdir=False )
        lw.log( loglines )
        if exists:
            success, loglines = deleteFile( newnfopath )
            lw.log( loglines )
        loglines, fin = readFile( nfotemplate )
        lw.log (loglines )
        if fin:
            newnfo = replaceWords( fin, replacement_dic )
            success, loglines = writeFile( newnfo, newnfopath, wtype='w' )
            lw.log( loglines )


    def _generate_thumbnail( self, videopath, thumbpath ):
        if not gen_thumbs:
            lw.log( ['thumbnail generation disabled in settings'] )
            return
        exists, loglines = checkPath( thumbpath, createdir=False )
        lw.log( loglines )
        if exists:
            if self.SHOW not in config.Get( 'force_thumbs' ):
                lw.log( ['thumbnail exists and show is not in force_thumbs, skipping thumbnail generation'] )
                return
            else:
                lw.log( ['thumbnail exists but show is in force_thumbs, creating thumbnail'] )
        else:
            lw.log( ['thumb does not exist, creating thumbnail'] )
        vidcap = cv2.VideoCapture( videopath )
        num_frames = int( vidcap.get( cv2.CAP_PROP_FRAME_COUNT ) )
        fps = int( vidcap.get( cv2.CAP_PROP_FPS ) )
        lw.log( ['got numframes: %s and fps: %s' % (str( num_frames ), str( fps ))] )
        if num_frames < 30 and fps < 30:
            lw.log( ['probably an error when reading file with opencv, skipping thumbnail generation'] )
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
        lw.log( ['capturing frame %s from range %s - %s' % (str( frame_cap ), str( frame_start ), str( frame_end ))] )
        vidcap.set( cv2.CAP_PROP_POS_FRAMES,frame_cap )
        success, image = vidcap.read()
        if success:
            success, buffer = cv2.imencode(".jpg", image)
            if success:
                success, loglines = writeFile( buffer, thumbpath, wtype='wb' )
                lw.log( loglines )
            else:
                lw.log( ['unable to encode thumbnail'] )
        else:
            lw.log( ['unable to create thumnail: frame out of range'] )


    def _trigger_scan( self ):
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
        if use_websockets:
            self._trigger_via_websocket( jsondata )
        else:
            time.sleep( 20 ) #this is to allow time for a previous scan to finish before starting the next process
            for kodiurl in self.KODIURLS:
                success, loglines, data = JSONURL.Post( kodiurl, data=jsondata )
                lw.log( loglines )


    def _trigger_via_websocket( self, jsondata ):
        def on_message(ws, message):
            lw.log( ['got back: ' + message] )
            if "VideoLibrary.OnScanFinished" in message:
                lw.log( ['got back scan complete message, attempting to close websocket'] )
                ws.close()
            ws_aborttime = config.Get( 'aborttime' ) - 5
            if time.time() - self.WSTIME > ws_aborttime:
                raise WebSocketException( "process has taken longer than %s seconds - terminating" % str( ws_aborttime ) )
        def on_error(ws, error):
            lw.log( [error] )
            ws.close()
        def on_close(ws):
            lw.log( ['websocket connection closed'] )
        def on_open(ws):
            lw.log( ['sending: ' + jsondata] )
            ws.send( jsondata )
        for kodiurl in self.KODIURLS:
            ws = websocket.WebSocketApp( kodiurl, on_message = on_message, on_error = on_error, on_open = on_open, on_close = on_close )
            lw.log( ['websocket connection opening'] )
            self.WSTIME = time.time()
            ws.run_forever()
