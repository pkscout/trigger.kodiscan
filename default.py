# *  Credits:
# *
# *  original Check Analog Recorder code by pkscuot


import os, subprocess, sys, xbmc, xbmcaddon, xbmcvfs
import resources.lib.oauth2 as _oauth
import resources.lib.oauth2.clients.smtp as _smtp
from resources.common.fileops import deleteFile
from resources.common.xlogger import Logger

__addon__        = xbmcaddon.Addon()
__addonname__    = __addon__.getAddonInfo('id')
__addonversion__ = __addon__.getAddonInfo('version')
__addonpath__    = __addon__.getAddonInfo('path').decode('utf-8')
__addonicon__    = xbmc.translatePath('%s/icon.png' % __addonpath__ )
__language__     = __addon__.getLocalizedString

lw = Logger( '[Check Analog Recorder]' )

class Main:
    def __init__( self ):
        self._get_settings()
        self._init_vars()
        self._check_analog()


    def _check_analog( self ):
        folders, recordings = xbmcvfs.listdir( self.RECORDINGPATH )
        if not any(".ts" in s for s in recordings):
            lw.log( ['no test recording found, servo needs to be triggered'], xbmc.LOGNOTICE )
            self._trigger_servo()
            if self.SENDEMAIL == 'true':
                self._send_email( [] )
        else:
            lw.log( ['test recording found, need to delete it'], xbmc.LOGNOTICE )
            for recording in recordings:
                success, loglines = deleteFile( os.path.join( self.RECORDINGPATH, recording ) )

                
    def _get_settings( self ):
        self.RECORDINGPATH = __addon__.getSetting( "recording_path" )
        self.SENDEMAIL = __addon__.getSetting( "send_email" )
        self.GMAILACCOUNT = __addon__.getSetting( "from_email" )
        self.TOEMAIL = __addon__.getSetting( "to_email" )
        self.OAUTHTOKEN = __addon__.getSetting( "oauth_token" )
        self.OAUTHSECRET = __addon__.getSetting( "oauth_secret" )


    def _init_vars( self ):
        self.DATAROOT = xbmc.translatePath('special://profile/addon_data/%s' % __addonname__ ).decode('utf-8')


    def _send_email( self, extrainfo ):
        consumer = _oauth.Consumer('anonymous', 'anonymous')
        token = _oauth.Token(self.OAUTHTOKEN, self.OAUTHSECRET)
        url = "https://mail.google.com/mail/b/%s/smtp/" % self.GMAILACCOUNT
        conn = _smtp.SMTP('smtp.googlemail.com', 587)
        conn.set_debuglevel(True)
        conn.ehlo('test')
        conn.starttls()
        conn.ehlo()
        conn.authenticate(url, consumer, token)
        subject = "Test of Cablebox Failed"
        header = 'To:%s\nFrom: %s\nSubject:%s\n' % (self.TOEMAIL, self.GMAILACCOUNT, subject)
        msg = 'The test recording was not found.  The servo has been actived.'
        if extrainfo:
            msg = msg + '\n\n---extra information follows---\n'
            for line in extrainfo:
                msg = msg + line.__str__() + '\n'
        conn.sendmail(self.GMAILACCOUNT, self.TOEMAIL, header + msg + '\n\n')


    def _trigger_servo( self ):
        servo_prog = os.path.join( self.DATAROOT, 'servo.vbs' )
        if xbmcvfs.exists( servo_prog ):
            subprocess.call( servo_prog, shell=True )



if ( __name__ == "__main__" ):
    lw.log( ['script version %s started' % __addonversion__], xbmc.LOGNOTICE )
    Main()
lw.log( ['script stopped'], xbmc.LOGNOTICE )