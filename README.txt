trigger.xbmcscan
================
PLEASE NOTE THAT AS OF 0.5.0 THERE ARE SUBSTATIVE CHANGES. IF YOU ARE UPGRADING FROM 0.4.x OR EARLIER, IT WOULD BE A GOOD IDEA TO USE THE SETTINGS-EXAMPLE.PY FILE AGAIN FROM SCRATH AND READ THROUGH THIS README AGAIN.

This python script is designed to run in the NextPVR PostProcessing.bat file.  It takes the OID of a recording file and triggers a Kodi scan on the parent directory for the file.  The script also allows you to rename shows based on either the air date or the information in the NextPVR database.  The script uses pid locking to ensure only one instance is running at a time and will wait for another instance to finish before running (this helps if you have multiple shows ending at the same time).


Prerequisites:
1. You need to have python 2.7.x installed on your system (3.4.x might work, but I haven't tested it).
<https://www.python.org/downloads/>

2. You need to add the requests and xmltodict modules to your python install.
On 2.7.x you need to install pip first (3.4.x has pip included):
<http://stackoverflow.com/questions/4750806/how-to-install-pip-on-windows>
Then from the cmd window:   pip install requests
                            pip install xmltodict
                            
3. To use the faster scan complete check, you need to add the websocket-client module to your python install.  After install the script will use websockets to communicate with Kodi unless you turn it off.  See below for information on configuring Kodi to use websockets for communication.
From the cmd window:        pip install websocket-client

4. To use the automatic thumbnail generation, you need to add the opencv-python module (3.0 or later) to your python install.  After install the script will generate thumbs automatically unless you turn it off in the settings.
From the cmd window:        pip install opencv-python


Configuration:
---Kodi settings:
In SYSTEM->SETTINGS->SERVICES->REMOTE CONTROL:
  a. enable "Allow remote control from applications on this system"
If you are not using websocket support, then instead in SYSTEM->SETTINGS->SERVICES->WEBSERVER
  a. enable "Allow remote control via HTTP"
  b. set a user name and password (script default assumes kodi for both).
  c. if needed, change the port (i.e. if something else is running on 8080).
---Script settings:
In the data directory of the script, rename settings-example.py to settings.py.  Review the settings file and make changes as needed.  If you're not sure what a setting does even after reading the comments in the settings.py file, you can probably leave it at the default.


Usage:
The best thing to do is add the following line to you PostProcessing.bat file in the NPVR Scripts directory:

"C:\Python27\python.exe" "C:\CustomApps\trigger.kodiscan\execute.py" %3

Please change the python call to match the location of your python install.  Note that even if you have python in the system path, calling the script with just "python" doesn't seem to work.

You can call the script directly from the command prompt, you just have to pass the correct OID from the NPVR database in manually.


Copying files to a NAS:
With the appropriate settings (see nas_mount in settings file), this script will copy your files from your local NPVR machine to a remote NAS and update the location in NPVR.  This is handy if you use the local machine for recording but want to store the recordings on something with more space.


Using with Kodi SMB library paths:
If you are using your local machine as a SMB share for other Kodi clients (or copying the files to a NAS with SMB shares), you need to set the SMB path for the library so that the script can properly trigger a library scan (see smb_name in settings file).


Generating thumbnails:
With the appropriate settings, this script will generate thumbnails from a random frame in the video if NPVR didn't download one. This is mostly helpful in showing the images on the Estuary home screen immediately instead of having to go to the file, have Kodi generate an internal thumbnail, and then refresh the skin to load it.


Fixing File Names:
This script will do some very basic renaming and add an info file for shows you specify.  In the script's data directory you can rename fixes-example to fixes.  In that folder you place another folder that exactly matches the name of your show (NBC Nightly News and In the Flesh are included as samples).  You can also use a folder named 'default' (all lowercase).  That fix will be applied to all shows (unless there is a separate show directory).

---Renaming using a .nfo template:
The show folder needs a file called episode.nfo. That file is a template for the .nfo file the script will create so that XBMC scans the show correctly.  You can put any of the XBMC related information in that template you'd like.  When you look at the sample episode.nfo file, you'll see that there some placeholders that the script will insert at runtime:
    [SEASON] the season number of the show (will be zero if no season number was in the NextPVR database)
    [EPISODE] the episode number of the show (will be a sequential number if season is 0)
    [TITLE] the title of the episode as passed in by NextPVR.
    [DESC] the description from the NextPVR database.
    [AIRDATE] the last modification date of the recording file.

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
