# *  Credits:
# *
# *  v.1.0.0~beta6
# *  original Trigger Kodi Scan code by pkscout

import atexit, argparse, datetime, os, random, shutil, sqlite3, sys, time, xmltodict
import resources.config as config
from resources.common.xlogger import Logger
from resources.common.url import URL
from resources.common.fileops import readFile, writeFile, deleteFile, renameFile, checkPath
from resources.common.transforms import replaceWords
if sys.version_info < (3, 0):
    from ConfigParser import *
else:
    from configparser import *
if sys.version_info >= (2, 7):
    import json as _json
else:
    import simplejson as _json

p_folderpath, p_filename = os.path.split( os.path.realpath(__file__) )
checkPath( os.path.join( p_folderpath, 'data', 'logs', '' ) )
lw = Logger( logfile = os.path.join( p_folderpath, 'data', 'logs', 'logfile.log' ),
             numbackups = config.Get( 'logbackups' ), logdebug = str( config.Get( 'debug' ) ) )

if config.Get( 'use_websockets' ):
    try:
        import websocket
        use_websockets = True
    except ImportError:
        lw.log( ['websocket-client not installed, falling back to JSON over HTTP'] )
        use_websockets = False
if not use_websockets:
    JSONURL = URL( 'json', headers={'content-type':'application/json'} )
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

pid = str(os.getpid())
pidfile = os.path.join( p_folderpath, 'data', 'scan.pid' )
atexit.register( _deletePID )


class Main:
    def __init__( self ):
        self._setPID()
        self._parse_argv()
        self._init_vars()
        if not (self.FILEPATH == '' or config.Get( 'nas_mount' ) == ''):
            self._nas_copy()
        if not self.FILEPATH == '':
            if self.TYPE == config.Get( 'tv_dir' ):
                self._fixes()
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
        if use_websockets:
            self.KODIURLS = ['ws://%s:%s/jsponrpc' % (config.Get( 'kodiuri' ), config.Get( 'kodiwsport' ) )]
            for remote in config.Get( 'remotekodilist' ):
                self.KODIURLS.append( 'ws://%s:%s/jsponrpc' % (remote.get('kodiuri'), remote.get('kodiwsport') ) )
        else:
            self.KODIURLS = ['http://%s:%s@%s:%s/jsonrpc' % (config.Get( 'kodiuser' ), config.Get( 'kodipass' ), config.Get( 'kodiuri' ), config.Get( 'kodiport' ))]
            for remote in config.Get( 'remotekodilist' ):
                self.KODIURLS.append( 'http://%s:%s@%s:%s/jsonrpc' % (remote.get('kodiuser'), remote.get('kodipass'), remote.get('kodiuri'), remote.get('kodiport')) )
        #get all the data about the recording from the NPVR database
        try:
            db = sqlite3.connect( config.Get( 'db_loc' ) )
            cursor = db.cursor()
            cursor.execute( '''SELECT filename, event_details from SCHEDULED_RECORDING WHERE oid=?''', ( self.OID, ) )
            recording_info = cursor.fetchone()
            db.close()
        except sqlite3.OperationalError:
            lw.log( ['error connecting to NPVR database, exiting.'] )
            self.FILEPATH = ''
            return
        try:
            self.FILEPATH = recording_info[0]
        except KeyError:
            lw.log( ['no data returned from NPVR database, exiting.'] )
            self.FILEPATH = ''
            return
        self.FOLDERPATH, filename = os.path.split( self.FILEPATH )
        remainder, self.SHOW = os.path.split( self.FOLDERPATH )
        throwaway, self.TYPE = os.path.split( remainder )
        if config.Get( 'smb_name' ) == '':
            self.SMBPATH = ''
        else:
            self.SMBPATH = '%s/%s/%s' % (config.Get( 'smb_name' ), self.TYPE, self.SHOW )
        lw.log( ['the filepath is ' + self.FILEPATH, 'the folderpath is ' + self.FOLDERPATH, 'the type is ' + self.TYPE])
        self.EVENT_DETAILS = xmltodict.parse( recording_info[1] )
        lw.log( [self.EVENT_DETAILS] )
            

    def _nas_copy( self ):
        nas_fail = True
        try:
            lw.log( ['getting list of files from ' + self.FOLDERPATH] )
            files = os.listdir( self.FOLDERPATH )
        except OSError:
            lw.log( ['directory %s not found' % self.FOLDERPATH] )
            return
        lw.log( ['found: ', files] )
        for onefile in files:
            nas_fail = False
            if (os.path.splitext( onefile )[1] in config.Get( 'video_exts' )):
                filename = onefile
            org = os.path.join( self.FOLDERPATH, onefile )
            dest = os.path.join( config.Get( 'nas_mount' ), self.TYPE, self.SHOW, onefile )
            exists, loglines = checkPath( os.path.join( config.Get( 'nas_mount' ), self.TYPE, self.SHOW), create=True )
            lw.log( loglines )
            try:
                shutil.move( org, dest )
            except shutil.Error as e:
                lw.log( ['shutil error copying %s to %s' % (org, dest), e] )
                nas_fail = True
                break
            except Exception as e:
                lw.log( ['unknown error copying %s to %s' % (org, dest), e] )
                nas_fail = True
                break
        if nas_fail:
            self.FILEPATH = ''
        else:
            self.FILEPATH = os.path.join( config.Get( 'nas_mount' ), self.TYPE, self.SHOW, filename )
            self.FOLDERPATH, filename = os.path.split( self.FILEPATH )
            self._update_db( self.FILEPATH )


    def _fixes( self ):
        found_show = False
        fixes_dir = os.path.join( p_folderpath, 'data', 'fixes' )
        try:
            shows = os.listdir( fixes_dir )
        except:
            return
        lw.log( ['there are potential shows to fix'] )
        lw.log( shows )
        if self.SHOW.lower() in map( str.lower, shows ):
            lw.log( ['matched %s with shows to fix' % show] )
            show_fixdir = os.path.join( fixes_dir, self.SHOW )
            found_show = True
        elif "default" in map( str.lower, shows ):
            lw.log( ['found default fix, applying to %s' % self.SHOW] )
            show_fixdir = os.path.join( fixes_dir, 'default' )
            found_show = True
        if found_show:
            nfopath = os.path.join( show_fixdir, 'episode.nfo')
            jsonpath = os.path.join( show_fixdir, 'episode.json')
            exists, loglines = checkPath( jsonpath, create=False )
            lw.log( loglines )
            if exists:
               self._jsonfix( jsonpath )
               return
            exists, loglines = checkPath( nfopath, create=False )
            lw.log( loglines )
            if exists:
               self._nfofix( nfopath )

            
    def _jsonfix( self, jsonpath ):
        video_files = []
        nfo_files = []
        ext_dict = {}
        try:
            items = os.listdir( self.FOLDERPATH )
        except OSError:
            err_str = 'directory %s not found' % self.FOLDERPATH
            lw.log( [err_str, 'script stopped'] )
            sys.exit( err_str )
        jsondata = readFile( jsonpath )
        lw.log( ['-----JSON data-----', jsondata[1]] )
        episodes = _json.loads( jsondata[1] )
        for item in items:
            fileroot, ext = os.path.splitext( item )
            processfilepath = os.path.join( self.FOLDERPATH, item )
            last_mod = time.strftime( '%Y-%m-%d', time.localtime( os.path.getmtime( processfilepath ) ) )
            if ext in config.Get( 'video_exts' ):
                for key in episodes:
                    episode = episodes[key]
                    lw.log( ['comparing file last mod of %s with json record date of %s' % (last_mod, episode['record-date'])] )
                    if last_mod == episode['record-date']:
                        newfilename = '%s.S%sE%s.%s%s' % (self.SHOW, episode['season'], episode['episode'], episode['title'], ext)
                        newfilepath = os.path.join( self.FOLDERPATH, newfilename )
                        exists, loglines = checkPath( newfilepath, create=False )
                        lw.log( loglines )
                        if not exists:
                            success, loglines = renameFile( processfilepath, newfilepath )
                            lw.log( loglines )
                            if success:
                                self._update_db( newfilepath )
                        else:
                            lw.log( ['%s already has the correct file name' % processfilepath] )
                        break
                    

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
        ep_info = {}
        ep_info['airdate'] = time.strftime( '%Y-%m-%d', time.localtime( os.path.getmtime( self.FILEPATH ) ) )
        try:
            ep_info['season'] = self.EVENT_DETAILS["Event"]["Season"]
            ep_info['episode'] = self.EVENT_DETAILS["Event"]["Episode"]
        except KeyError:
            ep_info['season'] = '0'
            ep_info['episode'] = self._special_epnumber( video_files )
        try:
            ep_info['title'] = self.EVENT_DETAILS["Event"]["SubTitle"]
        except KeyError:
            ep_info['title'] = ep_info['airdate']
        if ep_info['title'] == None:
            ep_info['title'] = ep_info['airdate']
        try:
            ep_info['description'] = self.EVENT_DETAILS["Event"]["Description"]
        except KeyError:
            ep_info['description'] = ''
        if ep_info['description'] == None:
            ep_info['description'] = ''
        lw.log( [ep_info] )       
        if ep_info['season'] == '0':
            self._specialseason( nfotemplate, ep_info )
        else:
            self._write_nfofile( nfotemplate, ep_info, os.path.splitext( self.FILEPATH )[0] + '.nfo' )
            self._generate_thumbnail( os.path.join( self.FOLDERPATH, self.FILEPATH ), os.path.join( self.FOLDERPATH, os.path.splitext( self.FILEPATH )[0] + '-thumb.jpg' ) )


    def _generate_thumbnail( self, videopath, thumbpath ):
        if not gen_thumbs:
            lw.log( ['thumbnail generation disabled in settings'] )
            return
        exists, loglines = checkPath( thumbpath, create=False )
        lw.log( loglines )
        if exists:
            if not self.SHOW in config.Get( 'force_thumbs' ):
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
            cv2.imwrite( thumbpath, image )
            lw.log( ['successfully created thumbnail at %s' % thumbpath] )
        else:
            lw.log( ['unable to create thumnail: frame out of range'] )


    def _special_epnumber( self, video_files ):
        # this gets the next available special season episode number for use
        highest_special_ep = ''
        for videofile in video_files:
            if videofile.startswith( '%s.S00' % self.SHOW ):
                highest_special_ep = videofile
        if highest_special_ep:
            epsplit = highest_special_ep.split( '.' )
            for onepart in epsplit:
                if onepart.startswith( 'S00' ):
                    epnum = str( int( onepart[4:] ) + 1 )
        else:
            epnum = '1'
        lw.log( ['the episode number calculated for the special season is ' + epnum] )
        return epnum


    def _specialseason( self, nfotemplate, ep_info ):
        newfileroot = '%s.S00E%s.%s' % (self.SHOW, ep_info['episode'].zfill( 2 ), ep_info['title'])
        newfilename = newfileroot + '.' + self.FILEPATH.split( '.' )[-1]
        newfilepath = os.path.join( self.FOLDERPATH, newfilename )
        newnfoname = newfileroot + '.nfo'
        self._write_nfofile( nfotemplate, ep_info, newnfoname )
        success, loglines = renameFile( self.FILEPATH, newfilepath )
        self._generate_thumbnail( newfilepath, os.path.join( self.FOLDERPATH, newfileroot + '-thumb.jpg' ) )
        lw.log( loglines )
        self._update_db( newfilepath )


    def _trigger_scan( self ):
        jsondict = {}
        jsondict['id'] = '1'
        jsondict['jsonrpc'] = '2.0'
        jsondict['method'] = "VideoLibrary.Scan"
        if self.SMBPATH == '':
            jsondict['params'] = {"directory":self.FOLDERPATH}
        else:
            jsondict['params'] = {"directory":self.SMBPATH + '/'}        
        jsondata = _json.dumps( jsondict )
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


    def _update_db( self, newfilepath ):
        db = sqlite3.connect( config.Get( 'db_loc' ) )
        cursor = db.cursor()
        cursor.execute( '''UPDATE SCHEDULED_RECORDING SET filename=? WHERE oid=?''', ( newfilepath, self.OID ) )
        db.commit()
        db.close()
        lw.log( ['updated NPVR filename of OID %s to %s' % (self.OID, newfilepath)] )                   


    def _write_nfofile( self, nfotemplate, ep_info, newnfoname ):
        newnfopath = os.path.join( self.FOLDERPATH, newnfoname )
        replacement_dic = {
            '[SEASON]': ep_info['season'],
            '[EPISODE]' : ep_info['episode'],
            '[TITLE]' : ep_info['title'],
            '[DESC]' : ep_info['description'],
            '[AIRDATE]' : ep_info["airdate"]}
        exists, loglines = checkPath( newnfopath, create=False )
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


if ( __name__ == "__main__" ):
    lw.log( ['script started'], 'info' )
    Main()
lw.log( ['script finished'], 'info' )