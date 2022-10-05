# -*- coding: utf-8 -*-
###########################################################################
#    Copyright (C) 2005-2009 Håvard Gulldahl
#    <havard@lurtgjort.no>
#
#    Lisens: GPL2
#
# $Id$
###########################################################################

import sqlite3
import time
from typing import Optional
from .fakturakomponenter import FakturaKomponent


class FakturaHandling(FakturaKomponent):  #(fakturabibliotek.fakturaKomponent):
    _tabellnavn = "Handling"

    def __init__(self, db: sqlite3.Connection, Id: Optional[int] = None, navn: Optional[str] = None):
        self.db = db
        self.navn = navn
        if Id is None:
            Id = self.nyId()
        self._id = Id

    def nyId(self):
        self.c.execute("INSERT INTO %s (ID, navn) VALUES (NULL, ?)" % self._tabellnavn, (self.navn, ))
        self.db.commit()
        return self.c.lastrowid


class HistoriskHandling:
    handlingID = 0
    dato = 0
    suksess = 0
    navn = None
    forklaring = ''
    ordreID = 0
    db = None

    def handling(self):
        return FakturaHandling(self.db, self.handlingID)

    def settHandling(self, handling):
        assert isinstance(handling, FakturaHandling)
        self.handlingID = handling._id
        return True

    def finnHandling(self, navn):
        assert type(navn) in (str, )
        self.c.execute('SELECT ID FROM Handling WHERE navn=?', (navn, ))
        return FakturaHandling(self.db, self.c.fetchone()[0], navn)

    def registrerHandling(self):
        #skriver til databasen
        self.c.execute("INSERT INTO Historikk (ordreID, dato, handlingID, suksess, forklaring) VALUES (?,?,?,?,?)",
                       (self.ordreID, self.dato, self.handlingID, (self.suksess and 1) or 0, self.forklaring))
        self.db.commit()

    def __init__(self, ordre, suksess, forklaring=None):
        assert isinstance(ordre, fakturakomponenter.FakturaOrdre)  #fakturabibliotek.fakturaOrdre)
        self.db = ordre.db
        self.c = self.db.cursor()
        self.ordreID = ordre.ID
        self.dato = time.mktime(time.localtime())
        self.suksess = suksess
        self.forklaring = forklaring
        if self.navn is not None:
            self.settHandling(self.finnHandling(self.navn))
        self.registrerHandling()


class Opprettet(HistoriskHandling):
    navn = 'opprettet'


class Forfalt(HistoriskHandling):
    navn = 'forfalt'


class MarkertForfalt(HistoriskHandling):
    navn = 'markertForfalt'


class Purret(HistoriskHandling):
    navn = 'purret'


class Betalt(HistoriskHandling):
    navn = 'betalt'


class Avbetalt(HistoriskHandling):
    navn = 'avBetalt'


class Kansellert(HistoriskHandling):
    navn = 'kansellert'


class AvKansellert(HistoriskHandling):
    navn = 'avKansellert'


class SendtTilInkasso(HistoriskHandling):
    navn = 'sendtTilInkasso'


class Utskrift(HistoriskHandling):
    navn = 'utskrift'


class EpostSendt(HistoriskHandling):
    navn = 'epostSendt'


class EpostSendtSmtp(HistoriskHandling):
    navn = 'epostSendtSmtp'


class EpostSendtGmail(HistoriskHandling):
    navn = 'epostSendtGmail'


class EpostSendtSendmail(HistoriskHandling):
    navn = 'epostSendtSendmail'


class PDFEpost(HistoriskHandling):
    navn = 'pdfEpost'


class PDFPapir(HistoriskHandling):
    navn = 'pdfPapir'


class PDFSikkerhetskopi(HistoriskHandling):
    navn = 'pdfSikkerhetskopi'
