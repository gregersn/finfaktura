# -*- coding:utf8 -*-
# kate: indent-width 4;
###########################################################################
#    Copyright (C) 2008 Håvard Gulldahl
#    <havard@gulldahl.no>
#
#    Lisens: GPL2
#
# $Id: faktura.py 260 2008-05-11 08:59:23Z havard.gulldahl $
#
###########################################################################

import logging
from qtpy import QtWidgets

from finfaktura.fakturabibliotek import FakturaBibliotek
from .ui import epost_ui
from . import epost


class EpostOppsett(epost_ui.Ui_epostOppsett):

    def __init__(self, faktura: FakturaBibliotek):
        self.faktura = faktura
        self.gui = QtWidgets.QDialog()
        self.setupUi(self.gui)
        self._epostlosninger = [self.epostLosningAuto, self.epostLosningSmtp, self.epostLosningSendmail]
        self.epostLosningAuto.toggled.connect(lambda: self.roter_aktiv_seksjon('auto'))
        self.epostLosningSmtp.toggled.connect(lambda: self.roter_aktiv_seksjon('smtp'))
        self.epostLosningSendmail.toggled.connect(lambda: self.roter_aktiv_seksjon('sendmail'))
        self.epostLosningTest.clicked.connect(self.test_epost)

        self.vis()
        self.gui.show()

    def exec(self):
        res = self.gui.exec()
        if res == QtWidgets.QDialog.DialogCode.Accepted:
            logging.debug('oppdaterer')
            self.oppdater_epost()
        return res

    def vis(self):
        assert self.faktura.epostoppsett is not None
        if self.faktura.epostoppsett.bcc:
            self.sendKopi.setChecked(True)
            self.kopiAdresse.setText(self.faktura.epostoppsett.bcc)
        self.roter_aktiv_seksjon(epost.TRANSPORTMETODER[self.faktura.epostoppsett.transport])
        self._epostlosninger[self.faktura.epostoppsett.transport].setChecked(True)
        if self.faktura.epostoppsett.smtpserver:
            self.smtpServer.setText(self.faktura.epostoppsett.smtpserver)
        if self.faktura.epostoppsett.smtpport:
            self.smtpPort.setValue(self.faktura.epostoppsett.smtpport)
        self.smtpTLS.setChecked(self.faktura.epostoppsett.smtptls)
        self.smtpAuth.setChecked(self.faktura.epostoppsett.smtpauth)
        if self.faktura.epostoppsett.smtpbruker:  # husk brukernavn og passord for smtp
            self.smtpHuskEpost.setChecked(True)
            if self.faktura.epostoppsett.smtpbruker:
                self.smtpBrukernavn.setText(self.faktura.epostoppsett.smtpbruker)
            if self.faktura.epostoppsett.smtppassord:
                self.smtpPassord.setText(self.faktura.epostoppsett.smtppassord)
        if self.faktura.epostoppsett.sendmailsti:
            self.sendmailSti.setText(self.faktura.epostoppsett.sendmailsti)
        else:
            self.sendmailSti.setText('~')

    def oppdater_epost(self):
        logging.debug("lagrer epost")
        logging.debug('eposttransport: %s', self.finn_aktiv_transport())
        assert self.faktura.epostoppsett is not None
        self.faktura.epostoppsett.transport = self.finn_aktiv_transport()
        if not self.sendKopi.isChecked():
            self.kopiAdresse.setText('')
        self.faktura.epostoppsett.bcc = str(self.kopiAdresse.text())
        self.faktura.epostoppsett.smtpserver = str(self.smtpServer.text())
        self.faktura.epostoppsett.smtpport = self.smtpPort.value()
        self.faktura.epostoppsett.smtptls = self.smtpTLS.isChecked()
        self.faktura.epostoppsett.smtpauth = self.smtpAuth.isChecked()
        if self.smtpHuskEpost.isChecked():
            self.faktura.epostoppsett.smtpbruker = str(self.smtpBrukernavn.text())
            self.faktura.epostoppsett.smtppassord = str(self.smtpPassord.text())
        else:
            self.faktura.epostoppsett.smtpbruker = ''
            self.faktura.epostoppsett.smtppassord = ''
        self.faktura.epostoppsett.sendmailsti = str(self.sendmailSti.text())

    def roter_aktiv_seksjon(self, seksjon: str):
        logging.debug("roterer til %s er synlig", seksjon)
        bokser = {'smtp': self.boxSMTP, 'sendmail': self.boxSendmail}
        if seksjon == 'auto':  #vis alt
            list(map(lambda x: x.setEnabled(True), list(bokser.values())))
            return
        for merke, box in bokser.items():
            box.setEnabled(merke == seksjon)

    def test_epost(self):
        self.oppdater_epost()  # må lagre for å bruke de inntastede verdiene
        try:
            transport = self.faktura.testEpost(epost.TRANSPORTMETODER[self.finn_aktiv_transport()])
        except Exception as ex:
            logging.debug('Fikk feil: %s', ex)
            s = 'Epostoppsettet fungerer ikke. Oppgitt feilmelding:\n {ex.message} \n\nKontroller at de oppgitte innstillingene \ner korrekte'
            trans = getattr(ex, 'transport')
            if trans != 'auto':
                ex.transportmetoder.remove(trans)  # fjerner feilet metode fra tilgjengelig-liste
                s += f', eller prøv en annen metode.\nTilgjengelige metoder:\n{", ".join(ex.transportmetoder)}'
            self.alert(s)
        else:
            self.obs(f"Epostoppsettet fungerer. Bruker {transport}")
            idx = epost.TRANSPORTMETODER.index(transport)
            self._epostlosninger[idx].setChecked(True)
            #self.roterAktivSeksjon(transport)
            self.oppdater_epost()  # må lagre for å bruke den aktive løsningen

    def finn_aktiv_transport(self):
        for i, w in enumerate(self._epostlosninger):
            if w.isChecked():
                return i

        return None

    def alert(self, msg: str):
        QtWidgets.QMessageBox.critical(
            self.gui,
            "Feil!",
            msg,
            QtWidgets.QMessageBox.StandardButton.Ok,
        )

    def obs(self, msg: str):
        QtWidgets.QMessageBox.information(
            self.gui,
            "Obs!",
            msg,
            QtWidgets.QMessageBox.StandardButton.Ok,
        )

    #def epostVisAuth(self, vis):
    ##self.epostSmtpBrukernavn.setEnabled(vis)
    #self.epostSmtpPassord.setEnabled(vis)
