#v.0.1.0

try:
    import xbmc
    LOGTYPE = 'xbmc'
except:
    import logging, logging.handlers
    LOGTYPE = 'file'

#this class creates an object used to log stuff to the xbmc log file
class Logger():
    def __init__(self, preamble='', logfile='logfile.log'):
        self.logpreamble = preamble
        if LOGTYPE == 'file':
            self.logger = logging.getLogger('_logger')
            self.logger.setLevel(logging.DEBUG)
            lr = logging.handlers.TimedRotatingFileHandler( logfile, when='d', interval=1, backupCount=7, encoding=None, delay=False, utc=False )
            lr.setLevel( logging.DEBUG )
            lr.setFormatter( logging.Formatter( "%(asctime)-15s %(levelname)-8s %(message)s" ) )
            self.logger.addHandler( lr )


    def log( self, loglines, loglevel='' ):
        if LOGTYPE == 'xbmc' and not loglevel:
            loglevel = xbmc.LOGDEBUG
        for line in loglines:
            try:
                if type(line).__name__=='unicode':
                    line = line.encode('utf-8')
                str_line = line.__str__()
            except Exception, e:
                str_line = ''
                self._output( 'error parsing logline', loglevel )
                self._output( e, loglevel )
            if str_line:
                self._output( str_line, loglevel )


    def _output( self, line, loglevel ):
        if LOGTYPE == 'file':
            self._output_file( line )
        else:
            self._output_xbmc( line, loglevel )

                
    def _output_file( self, line ):
        try:
            self.logger.info( "%s %s" % (self.logpreamble, line.__str__()) )
        except Exception, e:
            self.logger.debug( "%s unable to output logline" % self.logpreamble )
            self.logger.debug( "%s %s" % (self.logpreamble, e.__str__()) )


    def _output_xbmc( self, line, loglevel ):
        try:
            xbmc.log( "%s %s" % (self.logpreamble, line.__str__()), loglevel)
        except Exception, e:
            xbmc.log( "%s unable to output logline" % self.logpreamble, loglevel)
            xbmc.log ("%s %s" % (self.logpreamble, e.__str__()), loglevel)    

