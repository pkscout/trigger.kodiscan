trigger.xbmcscan
================

This python script is designed to run after imageGrabLite (an external program used with NextPVR).  It takes the path to a recording file and triggers an XBMC scan on the parent directory for the file.  The script also allows you to rename shows based on their air date (using S00Exx).  The second part is in there because I was having some real problems getting imageGrabLite to rename and add .nfo files for some things like the local and national news.


Prerequisites:
1. You need to have python 2.7.x installed on your system (3.4.x might work, but I haven't tested it).
<https://www.python.org/downloads/>

2. You need to add the requests module to your install.
On 2.7.x you need to install pip first (3.4.x has pip included):
<http://stackoverflow.com/questions/4750806/how-to-install-pip-on-windows>
Then from the cmd window:   pip install requests


Configuration:
---XBMC settings:
In SYSTEM->SETTINGS->SERVICES->WEBSERVER
  a. enable "Allow control of XBMC via HTTP"
  b. set a user name and password
  c. if needed (i.e. if something else is running on 8080), change the port.
In SYSTEM->SETTINGS->SERVICES->REMOTE CONTROL:
  a. enable "Allow programs on this system to control XBMC.
---Script settings:
In the data directory, rename settings-example.py to settings.py.  Edit that file and put in the user name and password you set above.  If you changed the port, make sure the settings.py file has that port number.  The last line of the settings file is a list of extensions the script will consider as video files.  If you're using a video extension not in this list, you can just add it at the end.


Usage:
The best thing to do is add the following line to you PostPRocessing.bat file in the NPVR Scripts directory:

"C:\Python27\python.exe" "C:\CustomApps\trigger.xbmcscan\default.py" %1

Please change the python call to match the location of your python install.  Note that even if you have python in the system path, calling the script with just "python" doesn't seem to work.

You can call the script directly from the command prompt, you just have to pass the filename (with the complete path) in manually.


Fixing File Names:
In a few cases imageGrabLite wasn't very good at renaming file (mostly the local and national news).  So this script will do some very basic renaming and add an info file for shows you specify.

In the script's data directory you can rename fixes-example to fixes.  In that folder you place another folder that exactly matches the name of your show (NBC Nightly News is included as a sample).  In *that* folder goes a file called episode.nfo; that file is a template for the .nfo file the script will create so that XBMC scans the show correctly.  You can put any of the XBMC related information in that template you'd like.  When you look at the sample episode.nfo file, you'll see that there are two placeholders that the script will insert at runtime:
    [DATE] this is the last modification date of the file in question.
    [EPNUM] the next available S00Exx number available for use in this directory.
I use [DATE] both in the title and airdate field, as the things I'm renaming are all daily shows.