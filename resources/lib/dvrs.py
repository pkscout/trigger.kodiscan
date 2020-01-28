#v.1.0.1

import os, sqlite3, time, xmltodict

class NextPVR:
    def __init__( self, oid, config ):
        self.OID = oid
        self.DBLOC = config.Get( 'db_loc' )
        self.LOGLINES = []


    def GetRecordingInfo( self ):
        self.LOGLINES = []
        try:
            db = sqlite3.connect( self.DBLOC )
            cursor = db.cursor()
            cursor.execute( '''SELECT filename, event_details from SCHEDULED_RECORDING WHERE oid=?''', ( self.OID, ) )
            recording_info = cursor.fetchone()
            db.close()
        except sqlite3.OperationalError:
            loglines.append( 'error connecting to NPVR database' )
            filepath = ''
        try:
            filepath = recording_info[0]
        except KeyError:
            loglines.append( 'no data returned from NPVR database' )
            filepath = ''
        loglines.append( 'the filepath is %s' % filepath )
        try:
            event_details = xmltodict.parse( recording_info[1] )
        except KeyError:
            loglines.append( 'no data returned from NPVR database' )
            event_details = []
        ep_info = self._set_ep_info( event_details )
        return ep_info, self.LOGLINES


    def UpdateDVR( self, newfilepath ):
        self.LOGLINES = []
        db = sqlite3.connect( self.DBLOC )
        cursor = db.cursor()
        cursor.execute( '''UPDATE SCHEDULED_RECORDING SET filename=? WHERE oid=?''', ( newfilepath, self.OID ) )
        db.commit()
        db.close()
        loglines.append( 'updated NPVR filename of OID %s to %s' % (self.OID, newfilepath) )
        return self.LOGLINES


    def _set_ep_info( self, event_details ):
        ep_info = {}
        ep_info['filepath'] = filepath
        ep_info['airdate'] = time.strftime( '%Y-%m-%d', time.localtime( os.path.getmtime( filepath ) ) )
        try:
            ep_info['season'] = event_details["Event"]["Season"]
        except KeyError:
            ep_info['season'] = '0'
        try:
            ep_info['episode'] = event_details["Event"]["Episode"]
        except KeyError:
            ep_info['episode'] = ''
        try:
            ep_info['title'] = event_details["Event"]["SubTitle"]
        except KeyError:
            ep_info['title'] = ep_info['airdate']
        if ep_info['title'] is None:
            ep_info['title'] = ep_info['airdate']
        try:
            ep_info['description'] = event_details["Event"]["Description"]
        except KeyError:
            ep_info['description'] = ''
        if ep_info['description'] is None:
            ep_info['description'] = ''
        self.LOGLINES.extend( [ep_info] )
        return ep_info
