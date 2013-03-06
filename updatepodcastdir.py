#!/usr/bin/env python
#
# updatepodcastdir.py - scan a directory of .mp3 files, and generate an RSS feed
# for podcasting
#
# usage: updatepodcastdir.py [config file]
#

import xml.etree.ElementTree as etree
import sys, email.Utils, os, os.path, ConfigParser
import eyeD3
import urllib


def setItem(item, file):
    """Set the passed-in <item> element based on the mp3 file that was passed in

       Note: item is modified as a result of this call

       file is a fully-qualified pathname
    """

    # read the ID3 tag of the file passed in
    tag = eyeD3.Tag()
    tag.link(file)

    # pull title from the ID3 tag
    title_elem = etree.SubElement(item, "title")
    title_elem.text = tag.getTitle()

    # use wwwaudiofile (ID3V2 WOAF frame) for the URL
    link_elem = etree.SubElement(item, "link")
    try:
        # there may not be one of these; that's OK
        link_elem.text = tag.getURLs()[0].url
    except IndexError:
        pass

    # use the ID3 comment for the description
    desc_elem = etree.SubElement(item, "description")
    desc_elem.text = tag.getComment()

    # use the .mp3 file's date/time for the pubDate
    date_elem = etree.SubElement(item, "pubDate")
    date_elem.text = email.Utils.formatdate(os.path.getmtime(file))

    # the enclosure element is the actual link to the file
    enc_elem = etree.SubElement(item, "enclosure")
    # if there are spaces in the filename, they need to be encoded as %20
    # hence the call to urllib.quote()
    enc_elem.set("url", urlprefix + urllib.quote(os.path.basename(file)))
    enc_elem.set("length", str(os.path.getsize(file))) 
    enc_elem.set("type", {'.mp3': 'audio/mpeg', '.aac': 'audio/aac'}[os.path.splitext(file)[1].lower()])

    return 



# Entry point #################################################################

config = ConfigParser.ConfigParser()
# config file can be specified as a parameter on the command line
if (len(sys.argv) > 1):
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

# get a listing of .mp3 files in the mp3 directory
# how this works:
# os.listdir(mp3path) gives a list of everything in the mp3 directory
# A mapping is done on that list, which calls the lambda to join the mp3path
# with the file.  The result is a list of absolute pathnames (since listdir()
# returns only filenames).  This list is filtered with another lambda function.
# In order for filenames to stay in the list, they must be regular files, and 
# must have an extension of ".mp3" or ".aac" (case-insensitive)
files = filter(lambda x: os.path.isfile(x) and                                \
                         os.path.splitext(x)[1].lower() in [".mp3", ".aac"],  \
               map(lambda x: os.path.join(mp3path, x), os.listdir(mp3path)))

# sort the list with newest first
files.sort(lambda x, y: cmp(os.stat(y).st_mtime, os.stat(x).st_mtime))

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
# NEW
lastbuilddate = rssdoc.find("//channel/lastBuildDate")
lastbuilddate.text = email.Utils.formatdate()

# find the channel element (/rss/channel) and append an item for each .mp3 file
itemlist = rssdoc.findall("//channel")
for file in files:
    fileitem = etree.SubElement(itemlist[0], "item")
    setItem(fileitem, file)

# XML document is finished; serialize and write it out
rssdoc.write(rssoutfile, encoding="utf-8")
