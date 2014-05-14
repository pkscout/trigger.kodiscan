#v.0.1.0

import logging
try:
    import xbmc
except:
    pass

#this class creates an object used to log stuff to the xbmc log file
class Logger():
    def __init__(self, preamble='', logfile='xlogfile.log'):
        self.logpreamble = preamble
        self.logfile = logfile


    def log( self, loglines, loglevel='' ):
        if not loglevel:
            try:
                loglevel = xbmc.LOGDEBUG
            except:
                loglevel = 'file'
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
        if loglevel == 'file':
            self._output_file( line )
        else:
            self_output_xbmc( line, loglevel )

                
    def _output_file( self, line ):
        logging.basicConfig(level=logging.DEBUG, filename=self.logfile, filemode="a+", format="%(asctime)-15s %(levelname)-8s %(message)s")
        try:
            logging.info( "%s %s" % (self.logpreamble, line.__str__()) )
        except Exception, e:
            logging.info( "%s unable to output logline" % self.logpreamble )
            logging.info( "%s %s" % (self.logpreamble, e.__str__()) )


    def _output_xbmc( self, line, loglevel ):
        try:
            xbmc.log( "%s %s" % (self.logpreamble, line.__str__()), loglevel)
        except Exception, e:
            xbmc.log( "%s unable to output logline" % self.logpreamble, loglevel)
            xbmc.log ("%s %s" % (self.logpreamble, e.__str__()), loglevel)    

