#!/usr/bin/env python3 -d
###########################################################################
#    Copyright (C) 2005-2009 Håvard Gulldahl
#    <havard@lurtgjort.no>
#
#    Lisens: GPL2
#
# $Id$
###########################################################################
"""Hjelpefunksjoner."""

import os.path
import glob
import subprocess


def forbered_ressurser():
    """Kjører pyuic5 på de nødvendige filene"""
    ui_files = glob.glob(os.path.join('finfaktura', 'ui', '*.ui'))
    rc_files = [
        'faktura.qrc',
    ]

    for fil in ui_files:
        ret = subprocess.call(['pyuic5', '--import-from=finfaktura.ui', '-x', '-o', os.path.splitext(fil)[0] + '_ui.py', fil])
        print(f"{fil}: {sjekk_status(ret)}")

    for f in rc_files:
        plassering = os.path.join('finfaktura', 'ui', os.path.splitext(f)[0] + '_rc.py')
        ret = subprocess.call(['pyrcc5', '-o', plassering, f])
        print("%s -> %s: %s" % (f, plassering, sjekk_status(ret)))

def sjekk_status(status: int):
    """Gjør status-kode til streng"""
    if status == 0:
        return "OK"
    return "FEIL"
