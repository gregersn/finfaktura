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
    """Kjører pyuic6 på de nødvendige filene"""
    ui_files = glob.glob(os.path.join('finfaktura', 'ui', '*.ui'))

    for fil in ui_files:
        ret = subprocess.call(['pyuic6', '-x', '-o', os.path.splitext(fil)[0] + '_ui.py', fil])
        print(f"{fil}: {sjekk_status(ret)}")


def sjekk_status(status: int):
    """Gjør status-kode til streng"""
    if status == 0:
        return "OK"
    return "FEIL"
