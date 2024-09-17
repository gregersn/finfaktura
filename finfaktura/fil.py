# -*- coding: utf-8 -*-
# kate: indent-width 4;
###########################################################################
#    Copyright (C) 2005-2009 Håvard Gulldahl
#    <havard@lurtgjort.no>
#
#    Lisens: GPL2
#
# $Id: oppgradering.py 217 2007-05-02 23:25:16Z havard.dahle $
###########################################################################

from pathlib import Path
import logging
import subprocess
from qtpy import QtCore, QtGui, QtWidgets

PDFVIS = "/usr/bin/xdg-open"


def vis(filnavn: Path, program: str = PDFVIS):
    if '%s' in program:
        command = (program % filnavn).split(' ')
    else:
        command = (program, filnavn)
    logging.debug('kommando: %s', command)
    try:
        subprocess.call(command)
    except Exception as xxx_todo_changeme:
        (e) = xxx_todo_changeme
        logging.exception(e)
        QtWidgets.QMessageBox.information(None, "Obs!", "Kunne ikke åpne PDF: %s.\nPrøver igjen, nå med systemets pdf-leser." % str(e),
                                          QtWidgets.QMessageBox.Ok)
        return QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(filnavn)))
