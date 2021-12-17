#!/usr/bin/env python

import os
import sys
import time
import traceback

from calibre.customize import (FileTypePlugin)
from calibre_plugins.azw6_image_merge import mobiparse, mobimergehdimage

__license__ = "GPL v3"
__copyright__ = "2021, Andrew Timson"
__version__ = "1.0.0"

PLUGIN_NAME = "AZW6 Image Merge"
PLUGIN_VERSION_TUPLE = tuple([int(x) for x in __version__.split(".")])
PLUGIN_VERSION = ".".join([str(x)for x in PLUGIN_VERSION_TUPLE])


if sys.version_info[0] == 2:
    str = type("")

class AZW6ImageMergeException(Exception):
    pass

# Wrap a stream so that output gets flushed immediately
# and also make sure that any unicode strings get safely
# encoded using "replace" before writing them.
class SafeUnbuffered:
    def __init__(self, stream):
        self.stream = stream
        self.encoding = stream.encoding
        if self.encoding == None:
            self.encoding = "utf-8"
    def write(self, data):
        if isinstance(data,str):
            data = data.encode(self.encoding,"replace")
        try:
            self.stream.buffer.write(data)
            self.stream.buffer.flush()
        except:
            # We can do nothing if a write fails
            pass
    def __getattr__(self, attr):
        return getattr(self.stream, attr)

class AZW6Input(FileTypePlugin):
    name = "AZW6 Image Merge"
    author = "Andrew Timson"
    # The original Kindle for PC file will have an AZW extension, though DeDRM will change it to AZW3.
    file_types = set(["azw"])
    on_import = True
    version = PLUGIN_VERSION_TUPLE
    minimum_calibre_version = (5, 0, 0)
    supported_platforms = ["windows", "osx", "linux"]
    description = "Hydrate Amazon AZW3 file with full images from Amazon AZW6 sidecar file."
    priority = 550 # Must be lower than DeDRM = 600

    def run(self, path_to_ebook):

        # make sure any unicode output gets converted safely with 'replace'
        sys.stdout=SafeUnbuffered(sys.stdout)
        sys.stderr=SafeUnbuffered(sys.stderr)

        print("{0} v{1}: Trying to process {2}".format(PLUGIN_NAME, PLUGIN_VERSION, os.path.basename(path_to_ebook)))

        newbooktype = os.path.splitext(path_to_ebook)[1].lower()[1:]
        origbooktype = os.path.splitext(self.original_path_to_file)[1].lower()[1:]
        if origbooktype == "azw" and newbooktype == "azw3":
            # Kindle for PC downloads with a .azw extension, while the DeDRM plugin changes eligible main files to AZW3.
            # It's possible this won't work as expected for DRM-free files; if so, change the newbooktype logic to support
            # both azw and azw3 extensions.
            decrypted_ebook = self.process_kindle_file(path_to_ebook)
        else:
            print("Unknown booktype {0}. Passing back to calibre unchanged".format(newbooktype))
            return path_to_ebook
        return decrypted_ebook

    def process_kindle_file(self, path_to_ebook):

        book = self.get_merged_book(path_to_ebook)
        
        # Even if we made no changes we write out a new copy of the file.
        of = self.temporary_file(book.get_book_extension())
        book.write_to_file(of.name)
        of.close()
        return of.name
    
    def get_merged_book(self, infile, starttime = time.time()):
        # handle the obvious cases at the beginning
        if not os.path.isfile(infile):
            # This is a legitimate issue we want to bubble up.
            raise AZW6ImageMergeException(u"Input file does not exist.")
        mobi = True
        magic8 = open(infile,'rb').read(8)
        if magic8 == '\xeaDRMION\xee':
            # KFX
            mobi = False
        magic3 = magic8[:3]
        if magic3 == 'TPZ':
            mobi = False
        if magic8[:4] != 'PK\x03\x04' and mobi:
            mb = mobiparse.MobiBook(infile)
            mb.load_book()
        
            import glob

            bookparentpath = os.path.dirname(os.path.abspath(self.original_path_to_file))
            print(u"Checking in: %s" % bookparentpath)
            azwresfiles = glob.glob(bookparentpath + "/*.azw.res")
            if azwresfiles != []:
                if len(azwresfiles) == 1:
                    print(u"HDImage Container file is found: %s" % os.path.basename(azwresfiles[0]))
                    print(u"HDImage merge start...")
                    try:
                        hdimage_merger = mobimergehdimage.MobiMergeHDImage(mb.mobi_data)
                        hdimage_merger.load_azwres(azwresfiles[0])
                        print("AZW loaded")
                        mb.mobi_data = hdimage_merger.merge()
                        print(u"HDImage merge succeeded after {0:.1f} seconds".format(time.time()-starttime))
                    except Exception as e:
                        traceback.print_exception(None, e, e.__traceback__)
                        print(u"Merge failed. Skipping...")
                else:
                    print(u"Multiple HDImage Container files found. This is not an AZW6 book. Skipping...")
            else:
                print("No HDImage Container file found. Skipping...")

        return mb
