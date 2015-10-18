# *  Credits:
# *
# *  v.0.3.3
# *  original Trigger XBMC Scan code by pkscout


import argparse, datetime, os, random, sqlite3, sys, time, xmltodict
from ConfigParser import *
from resources.common.xlogger import Logger
from resources.common.url import URL
from resources.common.fileops import readFile, writeFile, deleteFile, checkPath
from resources.common.transforms import replaceWords
if sys.version_info >= (2, 7):
    import json as _json
else:
    import simplejson as _json

p_folderpath, p_filename = os.path.split( os.path.realpath(__file__) )
lw = Logger( logfile = os.path.join( p_folderpath, 'data', 'logfile.log' ) )
JSONURL = URL( 'json', headers={'content-type':'application/json'} )

try:
    import data.settings as settings
except ImportError:
    err_str = 'no settings file found at %s' % os.path.join ( p_folderpath, 'data', 'settings.py' )
    lw.log( [err_str, 'script stopped'] )
    sys.exit( err_str )
try:
    settings.xbmcuser
    settings.xbmcpass
    settings.xbmcuri
    settings.xbmcport
    settings.video_exts
    settings.db_loc
except AttributeError:
    err_str = 'Settings file does not have all required fields. Please check settings-example.py for required settings.'
    lw.log( [err_str, 'script stopped'] )
    sys.exit( err_str )


class Main:
    def __init__( self ):
        self._parse_argv()
        self._init_vars()
        if not self.FILEPATH == '':
            self._fixes()
            self._trigger_scan()
        
                
    def _init_vars( self ):
        self.XBMCURL = 'http://%s:%s@%s:%s/jsonrpc' % (settings.xbmcuser, settings.xbmcpass, settings.xbmcuri, settings.xbmcport)
        #get all the data about the recording from the NPVR database
        try:
            db = sqlite3.connect(settings.db_loc)
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
        self.EVENT_DETAILS = xmltodict.parse( recording_info[1] )
        lw.log( [self.EVENT_DETAILS] )
        self.FOLDERPATH, filename = os.path.split( self.FILEPATH )


    def _fixes( self ):
        fixes_dir = os.path.join( p_folderpath, 'data', 'fixes' )
        try:
            shows = os.listdir( fixes_dir )
        except:
            return
        lw.log( ['there are potential shows to fix'] )
        lw.log( shows )
        throwaway, show = os.path.split( self.FOLDERPATH )
        if show.lower() in map( str.lower, shows ):
            lw.log( ['matched %s with shows to fix' % show] )
            show_fixdir = os.path.join( fixes_dir, show )
            nfopath = os.path.join( show_fixdir, 'episode.nfo')
            jsonpath = os.path.join( show_fixdir, 'episode.json')
            exists, loglines = checkPath( jsonpath, create=False )
            lw.log( loglines )
            if exists:
               self._jsonfix( show, jsonpath )
               return
            exists, loglines = checkPath( nfopath, create=False )
            lw.log( loglines )
            if exists:
               self._nfofix( show, nfopath )

            
    def _jsonfix( self, show, jsonpath ):
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
            if ext in settings.video_exts :
                for key in episodes:
                    episode = episodes[key]
                    lw.log( ['comparing file last mod of %s with json record date of %s' % (last_mod, episode['record-date'])] )
                    if last_mod == episode['record-date']:
                        newfilename = '%s.S%sE%s.%s%s' % (show, episode['season'], episode['episode'], episode['title'], ext)
                        newfilepath = os.path.join( self.FOLDERPATH, newfilename )
                        exists, loglines = checkPath( newfilepath, create=False )
                        lw.log( loglines )
                        if not exists:
                            try:
                                os.rename( processfilepath, newfilepath )
                            except OSError:
                                lw.log( ['%s not found, aborting fix' % processfilepath] )
                                break
                            lw.log( ['renamed %s to %s' % (processfilepath, newfilepath)] )
                            self._update_db( newfilepath )
                        else:
                            lw.log( ['%s already has the correct file name' % processfilepath] )
                        break
                    

    def _nfofix( self, show, nfotemplate ):
        video_files = []
        nfo_files = []
        ext_dict = {}
        try:
            items = os.listdir( self.FOLDERPATH )
        except OSError:
            err_str = 'directory %s not found' % self.FOLDERPATH
            lw.log( [err_str, 'script stopped'] )
            sys.exit( err_str )
        for item in items:
            fileroot, ext = os.path.splitext( item )
            if ext == '.nfo':
                nfo_files.append( fileroot )
            elif ext in settings.video_exts :
                video_files.append( fileroot )
                ext_dict[fileroot] = ext
        lw.log( ['comparing nfo file list with video file list'] )
        lw.log( ['nfo files:', nfo_files, 'video files:', video_files] )
        for nfo_file in nfo_files:
            if (not nfo_file in video_files) and (not nfo_file == 'tvshow'):
                os.remove( os.path.join( self.FOLDERPATH, nfo_file + '.nfo' ) )
        ep_info = {}
        try:
            ep_info['season'] = self.EVENT_DETAILS["Event"]["Season"]
            ep_info['episode'] = self.EVENT_DETAILS["Event"]["Episode"]
            has_season_ep = True
        except KeyError:
            ep_info['season'] = '0'
            ep_info['episode'] = ''
            has_season_ep = False
        try:
            ep_info['title'] = self.EVENT_DETAILS["Event"]["SubTitle"]
        except KeyError:
            ep_info['title'] = ''
        try:
            ep_info['description'] = self.EVENT_DETAILS["Event"]["Description"]
        except KeyError:
            ep_info['description'] = ''
        ep_info['airdate'] = time.strftime( '%Y-%m-%d', time.localtime( os.path.getmtime( self.FILEPATH ) ) )
        lw.log( [ep_info] )       
        if has_season_ep:
            self._regularseason( show, nfotemplate, ep_info )
        else:
            self._specialseason( video_files, nfo_files, ext_dict, show, nfotemplate, ep_info )


    def _regularseason( self, show, nfotemplate, ep_info ):
        newnfoname = os.path.splitext( self.FILEPATH )[0] + '.nfo'
        self._write_nfofile( nfotemplate, ep_info, newnfoname )


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


    def _specialseason( self, video_files, nfo_files, ext_dict, show, nfotemplate, ep_info ):
        processfiles = []
        for video_file in video_files:
            if not video_file in nfo_files:
                processfiles.append( video_file + ext_dict[video_file] )
        epnum = len( video_files )
        for processfile in processfiles:
            renamed = False
            processfilepath = os.path.join (self.FOLDERPATH, processfile )
            while not renamed:
                newfileroot = '%s.S00E%s.%s' % (show, str( epnum ).zfill( 2 ), ep_info["airdate"])
                newfilename = newfileroot + '.' + processfile.split( '.')[-1]
                newfilepath = os.path.join( self.FOLDERPATH, newfilename )
                newnfoname = newfileroot + '.nfo'
                if not newfileroot in video_files:
                    ep_info['episode'] = str( epnum )
                    self._write_nfofile( nfotemplate, ep_info, newnfoname )
                    try:
                        os.rename( processfilepath, newfilepath )
                    except OSError:
                        lw.log( ['%s not found, aborting fix' % processfilepath] )
                        break
                    renamed = True
                    video_files.append( newfileroot )
                    lw.log( ['renamed %s to %s' % (processfile, newfilename)] )
                    self._update_db( newfilepath )
                epnum += 1


    def _trigger_scan( self ):
        jsondict = {}
        jsondict['id'] = '1'
        jsondict['jsonrpc'] = '2.0'
        jsondict['method'] = "VideoLibrary.Scan"
        jsondict['params'] = {"directory":self.FOLDERPATH}
        jsondata = _json.dumps( jsondict )
        time.sleep( random.randint( 5, 30 ) )
        success, loglines, data = JSONURL.Post( self.XBMCURL, data=jsondata )
        lw.log( loglines )


    def _update_db( self, newfilepath ):
        db = sqlite3.connect(settings.db_loc)
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
            success, loglines = writeFile( newnfo, newnfopath )
            lw.log( loglines )


if ( __name__ == "__main__" ):
    lw.log( ['script started'], 'info' )
    Main()
lw.log( ['script stopped'], 'info' )