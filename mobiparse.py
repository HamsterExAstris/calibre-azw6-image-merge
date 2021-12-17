#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# mobiparse.py
# Copyright © 2008 The Dark Reverser
# Portions © 2008–2020 Apprentice Harper et al.

from __future__ import print_function
__license__ = 'GPL v3'
__version__ = "1.0"

# This is a python script. You need a Python interpreter to run it.
# For example, ActiveState Python, which exists for windows.
#
# Changelog
#  1.00 - Initial version, based on v1.00 of mobidedrm.py.

import struct

class ParseException(Exception):
    pass

#
# MobiBook Utility Routines
#

class MobiBook:
    def load_section(self, section):
        if (section + 1 == self.num_sections):
            endoff = len(self.data_file)
        else:
            endoff = self.sections[section + 1][0]
        off = self.sections[section][0]
        return self.data_file[off:endoff]

    def __init__(self, infile):
        # initial coherence check on file
        self.data_file = open(infile, 'rb').read()
        self.mobi_data = ''
        header = self.data_file[0:78]
        magic = header[0x3C:0x3C+8]
        if magic != b'BOOKMOBI' and magic != b'TEXtREAd':
            raise ParseException("Invalid file format")

        # build up section offset and flag info
        self.num_sections, = struct.unpack('>H', header[76:78])
        self.sections = []
        for i in range(self.num_sections):
            offset, a1,a2,a3,a4 = struct.unpack('>LBBBB', self.data_file[78+i*8:78+i*8+8])
            flags, val = a1, a2<<16|a3<<8|a4
            self.sections.append( (offset, flags, val) )

        # parse information from section 0
        self.sect = self.load_section(0)

        # det default values before PalmDoc test
        self.print_replica = False
        self.mobi_version = -1

        if magic == b'BOOKMOBI':
            self.mobi_version, = struct.unpack('>L',self.sect[0x68:0x6C])

    def write_to_file(self, outpath):
        open(outpath,'wb').write(self.mobi_data)

    def get_book_extension(self):
        if self.print_replica:
            return ".azw4"
        if self.mobi_version >= 8:
            return ".azw3"
        return ".mobi"

    # pids in pidlist may be unicode or bytearrays or bytes
    def load_book(self):
        crypto_type, = struct.unpack('>H', self.sect[0xC:0xC+2])
        if crypto_type == 0:
            # we must still check for Print Replica
            self.print_replica = (self.load_section(1)[0:4] == '%MOP')
            self.mobi_data = self.data_file
            return
        raise ParseException("Cannot process encrypted books. (Detected Mobipocket encryption type {0:d}.)".format(crypto_type))
