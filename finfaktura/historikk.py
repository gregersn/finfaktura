# -*- coding: utf-8 -*-
###########################################################################
#    Copyright (C) 2005-2009 Håvard Gulldahl
#    <havard@lurtgjort.no>
#
#    Lisens: GPL2
#
# $Id$
###########################################################################

import time
import sqlite3
from typing import Optional
from . import fakturakomponenter


class fakturaHandling(fakturakomponenter.FakturaKomponent):  #(fakturabibliotek.fakturaKomponent):
    tabellnavn = "Handling"

    def __init__(self, db: sqlite3.Connection, Id=None, navn=None):
        self.db = db
        self.navn = navn
        if Id is None:
            Id = self.nyId()
        self._id = Id

    def nyId(self):
        self.c.execute("INSERT INTO %s (ID, navn) VALUES (NULL, ?)" % self.tabellnavn, (self.navn, ))
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
        return fakturaHandling(self.db, self.handlingID)

    def settHandling(self, handling):
        assert isinstance(handling, fakturaHandling)
        self.handlingID = handling._id
        return True

    def finnHandling(self, navn):
        assert type(navn) in (str, )
        self.c.execute('SELECT ID FROM Handling WHERE navn=?', (navn, ))
        return fakturaHandling(self.db, self.c.fetchone()[0], navn)

    def registrerHandling(self):
        #skriver til databasen
        self.c.execute("INSERT INTO Historikk (ordreID, dato, handlingID, suksess, forklaring) VALUES (?,?,?,?,?)",
                       (self.ordreID, self.dato, self.handlingID, (self.suksess and 1) or 0, self.forklaring))
        self.db.commit()

    def __init__(self, ordre: fakturakomponenter.fakturaOrdre, suksess: int, forklaring: Optional[str] = None):
        assert isinstance(ordre, fakturakomponenter.fakturaOrdre)  #fakturabibliotek.fakturaOrdre)
        self.db = ordre.db
        self.c = self.db.cursor()
        self.ordreID = ordre.ID
        self.dato = time.mktime(time.localtime())
        self.suksess = suksess
        self.forklaring = forklaring
        if self.navn is not None:
            self.settHandling(self.finnHandling(self.navn))
        self.registrerHandling()


class opprettet(HistoriskHandling):
    navn = 'opprettet'


class forfalt(HistoriskHandling):
    navn = 'forfalt'


class markertForfalt(HistoriskHandling):
    navn = 'markertForfalt'


class purret(HistoriskHandling):
    navn = 'purret'


class betalt(HistoriskHandling):
    navn = 'betalt'


class avbetalt(HistoriskHandling):
    navn = 'avBetalt'


class kansellert(HistoriskHandling):
    navn = 'kansellert'


class avKansellert(HistoriskHandling):
    navn = 'avKansellert'


class sendtTilInkasso(HistoriskHandling):
    navn = 'sendtTilInkasso'


class utskrift(HistoriskHandling):
    navn = 'utskrift'


class epostSendt(HistoriskHandling):
    navn = 'epostSendt'


class epostSendtSmtp(HistoriskHandling):
    navn = 'epostSendtSmtp'


class epostSendtGmail(HistoriskHandling):
    navn = 'epostSendtGmail'


class epostSendtSendmail(HistoriskHandling):
    navn = 'epostSendtSendmail'


class pdfEpost(HistoriskHandling):
    navn = 'pdfEpost'


class pdfPapir(HistoriskHandling):
    navn = 'pdfPapir'


class pdfSikkerhetskopi(HistoriskHandling):
    navn = 'pdfSikkerhetskopi'
