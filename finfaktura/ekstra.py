#!/usr/bin/env python3 -d
# -*- coding:utf8 -*-
###########################################################################
#    Copyright (C) 2005-2009 Håvard Gulldahl
#    <havard@lurtgjort.no>
#
#    Lisens: GPL2
#
# $Id$
###########################################################################

import os.path, glob, subprocess


def forbered_ressurser():
    """Kjører pyuic6 på de nødvendige filene"""
    ui_files = glob.glob(os.path.join('finfaktura', 'ui', '*.ui'))

    for f in ui_files:
        ret = subprocess.call(['pyuic6', '-x', '-o', os.path.splitext(f)[0] + '_ui.py', f])
        print("%s: %s" % (f, ok(ret)))

def ok(status: int):
    if status == 0: return "OK"
    return "FEIL"
