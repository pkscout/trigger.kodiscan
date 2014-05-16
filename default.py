# *  Credits:
# *
# *  original Trigger XBMC Scan code by pkscuot


import argparse, datetime, ntpath, os, sys
from ConfigParser import *
from resources.common.xlogger import Logger
from resources.common.url import URL
if sys.version_info >= (2, 7):
    import json as _json
else:
    import simplejson as _json


p_folderpath, p_filename = ntpath.split( os.path.realpath(__file__) )
lw = Logger( logfile = os.path.join( p_folderpath, 'data', 'logfile.log' ) )
JSONURL = URL( 'json', headers={'content-type':'application/json'} )


class Main:
    def __init__( self ):
        self._parse_argv()
        self._init_vars()
        self._fixes()
        self._trigger_scan()
        
                
    def _init_vars( self ):
        try:
            import resources.settings as s
        except ImportError:
            err_str = 'no settings file found at %s' % os.path.join ( p_folderpath, 'settings.py' )
            lw.log( [err_str] )
            sys.exit( err_str )
        self.XBMCURL = 'http://%s:%s@%s:%s/jsonrpc' % (s.xbmcuser, s.xbmcpass, s.xbmcuri, s.xbmcport)
        self.FOLDERPATH, self.FILENAME = ntpath.split( self.FILEPATH )


    def _fixes( self ):
        try:
            shows = os.listdir( os.path.join( p_folderpath, 'data', 'fixes' ) )
        except:
            return
        lw.log( ['there are potential shows to fix'] )
        lw.log( shows )
        throwaway, show = ntpath.split( self.FOLDERPATH )
        if show in shows:
            lw.log( ['matched %s with shows to fix' % show] )
            renamed = False
            epnum = 1
            while not renamed:
                newfileroot = '%s.S00E%s' % (show, str( epnum ).zfill( 2 ))
                newfilename = newfileroot + '.%s' % self.FILENAME.split( '.')[-1]
                newnfoname = newfileroot + '.nfo'
                newfilepath = os.path.join( self.FOLDERPATH, newfilename )
                if os.path.exists( newfilepath ):
                    epnum += 1
                else:
                    try:
                        os.rename( self.FILEPATH, os.path.join( self.FOLDERPATH, newfilename ) )
                    except OSError:
                        lw.log( ['%s not found, aborting fixes' % self.FILEPATH] )
                        return
                    renamed = True
                    lw.log( ['renamed %s to %s' % (self.FILENAME, newfilename)] )
                    nfotemplate = os.path.join ( p_folderpath, 'data', 'fixes', show, 'episode.nfo' )
                    nfo = os.path.join( self.FOLDERPATH, newnfoname )
                    if os.path.exists( nfo ):
                        os.remove( nfo )
                    with open( nfo, "wt" ) as fout:
                        with open( nfotemplate, "rt" ) as fin:
                            for line in fin:
                                templine = line.replace( '[EPNUM]', str( epnum ) )
                                fout.write( templine.replace( '[DATE]', str( datetime.date.today() ) ) )
                    lw.log( ['added nfo file %s' % nfo] )


    def _parse_argv( self ):
        parser = argparse.ArgumentParser()
        parser.add_argument( "filepath", help="path to the video file (including file name)", nargs="+" )
        args = parser.parse_args()
        if len( args.filepath ) == 1:
            lw.log( ['got %s from command line' % args.filepath[0] ] )
            onearg = True
        else:
            lw.log( ['got something strange from the command line'] )
            lw.log( args.filepath )
            lw.log( ['will try and continue with the first argument'] )
            onearg = False
        self.FILEPATH = args.filepath[0]


    def _trigger_scan( self ):
        jsondict = {}
        jsondict['id'] = '1'
        jsondict['jsonrpc'] = '2.0'
        jsondict['method'] = "VideoLibrary.Scan"
        jsondict['params'] = {"directory":self.FOLDERPATH}
        jsondata = _json.dumps( jsondict )
        success, loglines, data = JSONURL.Post( self.XBMCURL, data=jsondata )
        lw.log( loglines )


if ( __name__ == "__main__" ):
    lw.log( ['script started'] )
    Main()
lw.log( ['script stopped'] )