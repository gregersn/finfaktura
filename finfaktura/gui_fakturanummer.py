#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# kate: indent-width 2; encoding utf-8
###########################################################################
#    Copyright (C) 2005-2009 Håvard Gulldahl
#    <havard@gulldahl.no>
#
#    Lisens: GPL2
#
# $Id: faktura.py 260 2008-05-11 08:59:23Z havard.gulldahl $
#
###########################################################################

import sys
import os
import os.path
import glob
from time import strftime, localtime
import logging
import sqlite3

from stat import ST_MTIME

from qtpy import QtWidgets
from qtpy.uic import loadUi

#from ui import fakturanummer_ui


class Nummersetter:

    def les_database_info(self, databasenavn: str):
        if not os.path.exists(databasenavn):
            return False
        db = sqlite3.connect(databasenavn)

        mtime = os.stat(databasenavn)[ST_MTIME]

        cursor = db.cursor()
        firmanavn = None
        fakturaer = None
        try:
            cursor.execute('SELECT firmanavn FROM Firma')
            firmanavn = cursor.fetchone()[0]
            cursor.execute('SELECT * FROM Ordrehode')
            fakturaer = len(cursor.fetchall())
            status = fakturaer == 0
        except sqlite3.Error:
            status = False
            firmanavn = 'Feil'

        ret = {
            'filnavn': databasenavn,
            'firmanavn': firmanavn,
            'fakturaer': fakturaer,
            'endret': mtime,
            'status': status,
        }
        return ret

    def sett_fakturanummer(self, databasenavn: str, fakturanummer: int):
        logging.debug("Skal sette fakturanr %s på db %s", fakturanummer, databasenavn)
        if not os.path.exists(databasenavn):
            return False
        db = sqlite3.connect(databasenavn)
        cursor = db.cursor()
        cursor.execute('SELECT * FROM Ordrehode')
        if len(cursor.fetchall()) > 0:
            raise Exception('Det er allerede laget fakturaer i denne databasen. Kan ikke sette fakturanummer.')
        cursor.execute('INSERT INTO Kunde (ID, navn, slettet) VALUES (1, "Tom kunde", 1)')
        cursor.execute('INSERT INTO Ordrehode (ID, tekst, kansellert, kundeID, ordredato, forfall) VALUES (?, "Tom faktura", 1, 1, 1, 1)',
                       (fakturanummer, ))
        db.commit()
        db.close()
        return True


class NummersetterGUI:

    def __init__(self):
        self.help = Nummersetter()
        filepath = os.path.join(os.path.dirname(__file__), 'ui/fakturanummer.ui')
        self.gui: QtWidgets.QWidget = load_ui.loadUi(filepath)
        assert self.gui is not None
        # self.gui.connect(self.gui.databasenavn, QtCore.SIGNAL('activated(QString)'), self.slotDatabaseValgt)
        # self.gui.connect(self.gui.settFakturanummer, QtCore.SIGNAL('clicked()'), self.slotSettFakturanummer)
        self.gui.show()
        self.gui.databasenavn.addItems(list(self.list_databaser()))
        self.vis_databasestatus()

    def list_databaser(self):
        if os.path.exists(os.getenv('FAKTURADB', '')):
            yield os.getenv('FAKTURADB')
        for d in (os.path.join(os.getenv('HOME', ''), '.finfaktura'), os.path.join(os.getenv('HOME', ''),
                                                                                   'finfaktura'), os.getenv('FAKTURADIR'), '.'):
            if not d:
                continue
            if not os.path.exists(d):
                continue
            for f in glob.glob(os.path.join(d, '*.db')):
                yield f
        yield '...'

    def slotDatabaseValgt(self, filename: str):
        logging.debug('valgte database: %s', filename)
        if filename == '...':
            filename = self.velg_database()
            self.gui.databasenavn.insertItem(-1, filename)
        self.vis_databasestatus()

    def vis_databasestatus(self):
        status = self.help.les_database_info(str(self.gui.databasenavn.currentText()))
        logging.debug('status:%s', status)
        if not status:
            return False
        self.gui.detaljerFilnavn.setText(status['filnavn'])
        self.gui.detaljerFirmanavn.setText(status['firmanavn'])
        self.gui.detaljerFakturaer.setText(str(status['fakturaer']))
        self.gui.detaljerEndretDato.setText(strftime('%Y-%m-%d %H:%M:%S', localtime(status['endret'])))
        self.gui.detaljerStatus.setText({True: '<b>Klar til å endres</b>', False: '<b>Kan ikke endres</b>'}[status['status']])
        self.gui.handlingsBoks.setEnabled(status['status'])

    def velg_database(self):
        selected_file = QtWidgets.QFileDialog.getOpenFileName(
            self.gui,
            'Velg database',
            os.getenv('HOME', '.'),
            "Databasefil (*.db)",
        )
        logging.debug('valgte fil: %s', selected_file)
        return selected_file

    def slotSettFakturanummer(self):
        fnr: int = self.gui.fakturanummer.value()
        logging.debug('Frste fakturanummer skal være %s', repr(fnr))
        if fnr < 1:
            QtWidgets.QMessageBox.critical(self.gui, "Feil fakturanummer",
                                           "Du må sette første fakturanummer (nummeret du ønsker at din første faktura skal få)")
            return False
        click = QtWidgets.QMessageBox.warning(
            self.gui,
            "Sette fakturanummer?",
            f"Advarsel! \nDu er nå i ferd med å endre fakturadatabasen, slik at neste faktura får løpenummer {fnr}. Dette kan ikke endres senere! \n\nEr du sikker? (Hvis du er i tvil, velg 'Nei/No')",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        logging.debug('vil gjøre %s', click)
        if click == QtWidgets.QMessageBox.StandardButton.Yes:
            logging.debug('ja')
            if self.help.sett_fakturanummer(str(self.gui.databasenavn.currentText()), fnr - 1):
                QtWidgets.QMessageBox.information(
                    self.gui,
                    "Fakturanummer endret",
                    f"Endret fakturanummer. Nå får neste faktura nummer {fnr}",
                )


if __name__ == '__main__':
    if '-d' in sys.argv:
        logging.basicConfig(level=logging.DEBUG)
    a = QtWidgets.QApplication(sys.argv)
    p = NummersetterGUI()
    a.exec()
