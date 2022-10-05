#!/usr/bin/python -d
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
    """Kjører pyrcc4 og pyuic4 på de nødvendige filene"""
    ui_files = glob.glob(os.path.join('finfaktura', 'ui', '*.ui'))
    rc_files = [
        'faktura.qrc',
    ]

    for f in ui_files:
        ret = subprocess.call(['pyuic5', '-x', '-o', os.path.splitext(f)[0] + '_ui.py', f])
        print("%s: %s" % (f, ok(ret)))
    for f in rc_files:
        plassering = os.path.join('finfaktura', 'ui', os.path.splitext(f)[0] + '_rc.py')
        ret = subprocess.call(['pyrcc5', '-o', plassering, f])
        print("%s -> %s: %s" % (f, plassering, ok(ret)))


def ok(status):
    if status == 0: return "OK"
    return "FEIL"
