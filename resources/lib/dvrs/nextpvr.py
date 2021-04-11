
import resources.lib.apis.nextpvr as nextpvr
import re
import time


class DVR:

    def __init__(self, config):
        self.APICALL = nextpvr.API(config.Get('dvr_host'), config.Get(
            'dvr_port'), config.Get('dvr_auth'), 'trigger.kodiscan')

    def GetRecordingInfo(self, oid):
        loglines = []
        info = {}
        success, loglines, results = self.APICALL.getRecordingList(
            recording_id=oid)
        if not success:
            return info, loglines
        try:
            recording = results['recordings'][0]
        except (KeyError, IndexError):
            return info, loglines
        info['filepath'] = recording.get('file', '')
        info['airdate'] = time.strftime(
            '%Y-%m-%d', time.localtime(recording.get('startTime')))
        if info['airdate'] == '1969-12-31':
            info['airdate'] = time.strftime('%Y-%m-%d', time.localtime())
        info['season'] = str(recording.get('season', '0'))
        info['episode'] = str(recording.get('episode', ''))
        info['title'] = re.sub(
            r'S[0-9]{2}E[0-9]{2} - ', '', recording.get('subtitle'))
        if not info['title']:
            info['title'] = info['airdate']
        info['description'] = recording.get('desc', '')
        return info, loglines
