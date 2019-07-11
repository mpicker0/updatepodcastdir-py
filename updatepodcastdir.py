#!/usr/bin/env python
#
# updatepodcastdir.py - scan a directory of .mp3 files, and generate an RSS feed
# for podcasting
#
# usage: updatepodcastdir.py [config_file]
#

import xml.etree.ElementTree as etree
import sys
import email.utils
import os
import os.path
import configparser
import urllib.parse
from fnmatch import fnmatch
from mutagen.easyid3 import EasyID3


def set_item(item, filename):
    """Set the passed-in <item> element based on the mp3 file that was passed in

       Note: item is modified as a result of this call

       filename is a fully-qualified pathname
    """

    # read the ID3 tag of the file passed in
    audiofile = EasyID3(filename)

    # pull title from the ID3 tag
    title_elem = etree.SubElement(item, 'title')
    title_elem.text = next(iter(audiofile.get('title') or []), None)

    # use wwwaudiofile (ID3V2 WOAF frame) for the URL
    link_elem = etree.SubElement(item, 'link')
    link_elem.text = next(iter(audiofile.get('website') or []), None)

    # use the .mp3 file's date/time for the pubDate
    date_elem = etree.SubElement(item, 'pubDate')
    date_elem.text = email.utils.formatdate(os.path.getmtime(file))

    # the enclosure element is the actual link to the file
    enc_elem = etree.SubElement(item, 'enclosure')
    enc_elem.set("url", urlprefix + urllib.parse.quote(os.path.basename(file)))
    enc_elem.set("length", str(os.path.getsize(file))) 
    enc_elem.set("type", {'.mp3': 'audio/mpeg', '.aac': 'audio/aac'}[os.path.splitext(file)[1].lower()])

    return 


config = configparser.ConfigParser()
# config file can be specified as a parameter on the command line
if len(sys.argv) > 1:
    configfile = sys.argv[1]
else:
    configfile = "updatepodcastdir.config"
config.read(configfile)

mp3path = config.get("paths", "mp3path")
rsstemplate = config.get("paths", "rsstemplate")
rssoutfile = config.get("paths", "rssoutfile")
urlprefix = config.get("web", "urlprefix")
maxitems = config.getint("misc", "maxitems")
deleteold = config.getboolean("misc", "deleteold")

# get a listing of .mp3/.aac files in the mp3 directory
files = [os.path.join(mp3path, f) for f in os.listdir(mp3path) if fnmatch(f, '*.mp3') or fnmatch(f, '*.aac')]

# sort the list with newest first
files.sort(key=lambda x: os.stat(x).st_mtime)

# prevent items beyond maxitems from appearing, optionally deleting them
while len(files) > maxitems:
    if deleteold:
        os.remove(files.pop())
    else:
        files.pop()

# now for the XML
# build a DOM representation of the template
rssdoc = etree.parse(rsstemplate)

# find the lastBuildDate and fill it in
lastbuilddate = rssdoc.find(".//channel/lastBuildDate")
lastbuilddate.text = email.utils.formatdate()

# find the channel element (/rss/channel) and append an item for each .mp3 file
itemlist = rssdoc.findall(".//channel")
for file in files:
    fileitem = etree.SubElement(itemlist[0], "item")
    set_item(fileitem, file)

# XML document is finished; serialize and write it out
rssdoc.write(rssoutfile, encoding="utf-8")
