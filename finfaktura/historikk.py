#!/usr/bin/env python
# -*- coding:utf8 -*-
###########################################################################
#    Copyright (C) 2006 - Håvard Dahle 
#    <havard@dahle.no>
#
#    Lisens: GPL2
#
# $Id$
###########################################################################

import fakturabibliotek 
#import sqlite
import types, sys, time

class fakturaHandling(fakturabibliotek.fakturaKomponent):
    _tabellnavn = "Handling"
    def __init__(self, db, Id = None, navn = None):
        self.db = db
        self.navn = navn
        if Id is None:
            Id = self.nyId()
        self._id = Id
        
    def nyId(self):
        self.c.execute("INSERT INTO %s (ID, navn) VALUES (NULL, ?)" % self._tabellnavn, (self.navn,))
        self.db.commit()
        return self.c.lastrowid
                
class historiker:
    
    def __init__(self, db):
        print type(db)
        assert isinstance(db, SQLType)
        self.db = db
        self.c  = db.cursor()
    
    def logg(self, handling):
        assert isinstance(handling, historiskHandling)
        self.c.execute("""INSERT INTO Historikk
                     (ordreID, dato, handlingID, suksess, forklaring)
                     VALUES
                     (?,?,?,?,?)""", dict(handling) )
        self.db.commit()
        
class historiskHandling:
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
        print handling
        self.handlingID = handling.ID
        return True
    
    def finnHandling(self, navn):
        assert type(navn) in types.StringTypes
        print 'SELECT ID FROM Handling WHERE navn=?', (navn,)
        self.c.execute('SELECT ID FROM Handling WHERE navn=?', (navn,))
        return fakturaHandling(self.db, self.c.fetchone()[0], navn)
        
    def __init__(self, ordre, suksess, forklaring=None):
        assert isinstance(ordre, fakturabibliotek.fakturaOrdre)
        self.db = ordre.db
        self.c  = self.db.cursor()
        self.ordreID = ordre.ID
        self.dato = time.mktime(time.localtime())
        self.suksess = suksess
        self.forklaring = forklaring
        if self.navn is not None:
            self.settHandling(self.finnHandling(self.navn))
        
class opprettet(historiskHandling):
    navn = 'opprettet'
        
class forfalt(historiskHandling):
    navn = 'forfalt'
    
class markertForfalt(historiskHandling):
    navn = 'markertForfalt'
    
class purret(historiskHandling):
    navn = 'purret'    
    
class betalt(historiskHandling):
    navn = 'betalt'    
    
class kansellert(historiskHandling):
    navn = 'kansellert'
    
class avKansellert(historiskHandling):
    navn = 'avKansellert'

class sendtTilInkasso(historiskHandling):
    navn = 'sendtTilInkasso'

class utskrift(historiskHandling):
    navn = 'utskrift'

class epostSendt(historiskHandling):
    navn = 'epostSendt'

class epostSendtSmtp(historiskHandling):
    navn = 'epostSendtSmtp'

class epostSendtGmail(historiskHandling):
    navn = 'epostSendtGmail'

class epostSendtSendmail(historiskHandling):
    navn = 'epostSendtSendmail'

class pdfEpost(historiskHandling):
    navn = 'pdfEpost'

class pdfPapir(historiskHandling):
    navn = 'pdfPapir'

class pdfSikkerhetskopi(historiskHandling):
    navn = 'pdfSikkerhetskopi'

