trigger.xbmcscan
================

This python script is designed to run in the NextPVR PostProcessing.bat file.  It takes the OID of a recording file and triggers an XBMC scan on the parent directory for the file.  The script also allows you to rename shows based on either the air date or the information in the NextPVR database.


Prerequisites:
1. You need to have python 2.7.x installed on your system (3.4.x might work, but I haven't tested it).
<https://www.python.org/downloads/>

2. You need to add the requests and xmltodict modules to your install.
On 2.7.x you need to install pip first (3.4.x has pip included):
<http://stackoverflow.com/questions/4750806/how-to-install-pip-on-windows>
Then from the cmd window:   pip install requests
                            pip install xmltodict


Configuration:
---XBMC settings:
In SYSTEM->SETTINGS->SERVICES->WEBSERVER
  a. enable "Allow control of XBMC via HTTP"
  b. set a user name and password
  c. if needed (i.e. if something else is running on 8080), change the port.
In SYSTEM->SETTINGS->SERVICES->REMOTE CONTROL:
  a. enable "Allow programs on this system to control XBMC.
---Script settings:
In the data directory, rename settings-example.py to settings.py.  Edit that file and put in the user name and password you set above.  If you changed the port, make sure the settings.py file has that port number.  If your NextPVR database is in a non-standard location, make that change as needed.  The last line of the settings file is a list of extensions the script will consider as video files.  If you're using a video extension not in this list, you can just add it at the end.


Usage:
The best thing to do is add the following line to you PostPRocessing.bat file in the NPVR Scripts directory:

"C:\Python27\python.exe" "C:\CustomApps\trigger.xbmcscan\default.py" %3

Please change the python call to match the location of your python install.  Note that even if you have python in the system path, calling the script with just "python" doesn't seem to work.

You can call the script directly from the command prompt, you just have to pass the correct OID in manually.


Fixing File Names:
This script will do some very basic renaming and add an info file for shows you specify.  In the script's data directory you can rename fixes-example to fixes.  In that folder you place another folder that exactly matches the name of your show (NBC Nightly News and In the Flesh are included as samples).
---Renaming using a .nfo template:
The show folder needs a file called episode.nfo. That file is a template for the .nfo file the script will create so that XBMC scans the show correctly.  You can put any of the XBMC related information in that template you'd like.  When you look at the sample episode.nfo file, you'll see that there some placeholders that the script will insert at runtime:
    [SEASON] the season number of the show (will be zero if no season number was in the NextPVR database)
    [EPISODE] the episode number of the show (will be a sequential number if season is 0)
    [TITLE] the title of the episode as passed in by NextPVR.
    [DESC] the description from the NextPVR database.
    [AIRDATE] the last modification date of the recording file.
    [CHANNELS] the audio channels available in the recording.    
    [DURATION] the duration of the recording (empty if start and end recording dates not available)


In the sample template [DATE] is used both in the title and airdate field because it's a daily show with no episode title.  See the NBC Nightly News folder as an example.
---Renaming using a json file:
The show folder needs a file called episode.json.  That file contains some data needed to rename the file so that XBMC can find it on thetvdb.com.  The basic format of the json file is:
{
    "ep1": {
        "record-date": "2014-05-10",
        "season": "02",
        "episode": "01",
        "title": "Episode 1"
    },
    "ep2": {
        "record-date": "2014-05-17",
        "season": "02",
        "episode": "02",
        "title": "Episode 2"
    }
}
There are two things to remember with the data in this file.  "ep1", "ep2", etc need to be unique for each record.  If you continue the naming format (i.e. "ep3", "ep4", etc.) you will be fine.  The record-date must be in the format yyyy-mm-dd and refers to the date on which you will be recording the episode.  This may or may not be the date the show aired according to thetvdb.com.  For instance, In the Flesh airs a week later on BBC America, and thetvdb.com data has the airdate set based on the BBC showing.  For the renaming to work if you recorded off BBC America, the json file for In the Flesh needs the dates the show is actually recorded instead of the BBC dates.


