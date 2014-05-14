# *  Credits:
# *
# *  original Trigger XBMC Scan code by pkscuot


import argparse, ntpath, os, sys
from resources.common.xlogger import Logger
from resources.common.url import URL
if sys.version_info >= (2, 7):
    import json as _json
else:
    import simplejson as _json


def _pathleaf( path ):
    path, filename = ntpath.split(path)
    return {"path":path, "filename":filename}


p_folderpath = _pathleaf( os.path.realpath(__file__) )['path']
lw = Logger( logfile = os.path.join( p_folderpath, 'logfile.log' ) )
JSONURL = URL( 'json', headers={'content-type':'application/json'} )

class Main:
    def __init__( self ):
        self._parse_argv()
        self._get_settings()
        self._init_vars()
        self._trigger_scan()
        
                
    def _get_settings( self ):
        pass


    def _init_vars( self ):
        xbmcuser = 'xbmc'
        xbmcpass = 'xbmc'
        xbmcuri = 'localhost'
        xbmcport = 8081
        self.XBMCURL = 'http://%s:%s@%s:%s/jsonrpc' % (xbmcuser, xbmcpass, xbmcuri, xbmcport)
        leaf = self._pathleaf( self.FILEPATH )
        self.FOLDERPATH = leaf['path']


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