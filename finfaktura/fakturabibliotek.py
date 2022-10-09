# -*- coding: utf-8 -*-
###########################################################################
#    Copyright (C) 2005-2009 Håvard Gulldahl og Håvard Sjøvoll
#    <havard@lurtgjort.no>, <sjovoll@ntnu.no>
#
#    Lisens: GPL2
#
# $Id$
###########################################################################

from pathlib import Path
import os
import sys
import os.path
import shutil
from time import time
import logging
from typing import Any, List, Optional
# import xml.etree.ElementTree  # help py2exe
import sqlite3

from . import fil
from .fakturakomponenter import FakturaOppsett, fakturaEpost, fakturaFirmainfo, \
        fakturaOrdre, fakturaVare, fakturaKunde, fakturaSikkerhetskopi

from . import epost

from .f60 import F60, REPORTLAB

PRODUKSJONSVERSJON = False  # Sett denne til True for å skjule funksjonalitet som ikke er ferdigstilt
DATABASEVERSJON = 3.1
DATABASENAVN = "faktura.db"
#DATABASECONVERTERS={"pdf":pdfdataToType}


class FakturaBibliotek:

    produksjonsversjon = False  # dersom false er vi i utvikling, ellers produksjon

    def __init__(self, db: sqlite3.Connection, sjekkVersjon: bool = True):
        self.db = db
        self.c = db.cursor()
        self.__firmainfo = None
        self.oppsett = FakturaOppsett(db, versjonsjekk=sjekkVersjon, apiversjon=DATABASEVERSJON)
        try:
            self.epostoppsett = fakturaEpost(db)
        except sqlite3.DatabaseError as e:
            if "no such table" in str(e).lower(): self.epostoppsett = None  ## for gammel versjon
            else: raise

    def versjon(self):
        v = self.oppsett.hentVersjon()
        if v is None: return 2.0  # før versjonsnummeret kom inn i db
        else: return v

    def hentKunde(self, kundeID: int):
        #assert(type(kundeID
        return fakturaKunde(self.db, kundeID)

    def hentKunder(self, inkluderSlettede: bool = False):
        sql = "SELECT ID FROM %s" % fakturaKunde._tabellnavn
        if not inkluderSlettede: sql += " WHERE slettet IS NULL OR slettet = 0"
        self.c.execute(sql)
        return [fakturaKunde(self.db, z[0]) for z in self.c.fetchall()]

    def nyKunde(self):
        return fakturaKunde(self.db)

    def hentVarer(self, inkluderSlettede: bool = False, sorterEtterKunde: bool = False):
        sql = "SELECT ID FROM %s" % fakturaVare._tabellnavn
        if not inkluderSlettede: sql += " WHERE slettet IS NULL OR slettet = 0"
        if sorterEtterKunde:
            sql += " ORDER BY kunde"
        self.c.execute(sql)
        return [fakturaVare(self.db, z[0]) for z in self.c.fetchall()]

    def nyVare(self):
        return fakturaVare(self.db)

    def hentVare(self, Id: Optional[int]):
        return fakturaVare(self.db, Id)

    def finnVareEllerLagNy(self, navn: str, pris: float, mva: int, enhet: str):
        sql = "SELECT ID FROM %s" % fakturaVare._tabellnavn
        sql += " WHERE navn=? AND pris=? AND mva=?"
        #print sql, navn, pris, mva
        self.c.execute(sql, (
            navn.strip(),
            pris,
            mva,
        ))
        try:
            return fakturaVare(self.db, self.c.fetchone()[0])
        except TypeError:
            # varen finnes ikke, lag ny og returner
            vare = self.nyVare()
            vare.navn = navn.strip()
            vare.pris = pris
            vare.mva = mva
            vare.enhet = enhet.strip()
            return vare

    def nyOrdre(self,
                kunde: Optional[fakturaKunde] = None,
                Id: Optional[int] = None,
                ordredato: Optional[int] = None,
                forfall: Optional[int] = None):
        return fakturaOrdre(self.db, kunde=kunde, Id=Id, firma=self.firmainfo(), dato=ordredato, forfall=forfall)

    def hentOrdrer(self):
        self.c.execute("SELECT ID FROM %s" % fakturaOrdre._tabellnavn)
        return [fakturaOrdre(self.db, Id=z[0]) for z in self.c.fetchall()]

    def firmainfo(self):
        if self.__firmainfo is not None:
            self.__firmainfo.hentEgenskaper()
            self.__firmainfo.sjekkData()
        else:
            self.__firmainfo = fakturaFirmainfo(self.db)
        return self.__firmainfo

    def hentEgenskapVerdier(self, tabell: str, egenskap: str):
        self.c.execute("SELECT DISTINCT %s FROM %s" % (egenskap, tabell))
        return [str(x[0]) for x in self.c.fetchall() if x[0]]

    def lagSikkerhetskopi(self, ordre: fakturaOrdre):
        s = fakturaSikkerhetskopi(self.db, ordre)
        #historikk.pdfSikkerhetskopi(ordre, True, "lagSikkerhetskopi)")
        return s

    def hentSikkerhetskopier(self):
        self.c.execute("SELECT ID FROM %s" % fakturaSikkerhetskopi._tabellnavn)
        return [fakturaSikkerhetskopi(self.db, Id=z[0]) for z in self.c.fetchall()]

    def sjekkSikkerhetskopier(self, lagNyAutomatisk: bool = False):
        sql = "SELECT Ordrehode.ID, Sikkerhetskopi.ID FROM Ordrehode LEFT OUTER JOIN Sikkerhetskopi ON Ordrehode.ID=Sikkerhetskopi.ordreID WHERE data IS NULL"
        self.c.execute(sql)
        ordrer: List[fakturaOrdre] = []
        for z in self.c.fetchall():
            logging.debug("Ordre #%i har ingen gyldig sikkerhetskopi!", z[0])
            o = fakturaOrdre(self.db, Id=z[0], firma=self.firmainfo())
            if lagNyAutomatisk:
                # merk evt. gammel sikkerhetskopi som ugyldig
                if z[1]:
                    s = fakturaSikkerhetskopi(self.db, Id=z[1])
                    s.data = None
                try:
                    self.lagSikkerhetskopi(o)
                    #historikk.pdfSikkerhetskopi(o, True, "sjekksikkerhetskopier(lagNyAutomatisk=True)")
                except FakturaFeil as e:
                    #historikk.pdfSikkerhetskopi(o, False, "sjekksikkerhetskopier: %s" % e)
                    raise SikkerhetskopiFeil('Kunne ikke lage sikkerhetskopi for ordre #%s! Årsak:\n%s' % (z[0], e))
            else:
                ordrer.append(o)
        return ordrer

    def lagPDF(self, ordre: fakturaOrdre, blankettType: str, _filnavn: Optional[str] = None):
        if not REPORTLAB:
            raise PDFFeil('Modulen "reportlab" er ikke installert. Uten denne kan du ikke lage pdf-fakturaer.')

        assert ordre.id is not None
        assert ordre.firma is not None
        pdf = F60(filnavn=_filnavn)
        #if not self.produksjonsversjon: pdf.settTestversjon()
        pdf.settFakturainfo(ordre.id, ordre.ordredato, ordre.forfall, ordre.tekst)
        pdf.settFirmainfo(ordre.firma.egenskaper)
        try:
            assert ordre.kunde is not None
            assert ordre.kunde.id is not None
            pdf.settKundeinfo(ordre.kunde.id, ordre.kunde.postadresse())
        except KundeFeil as e:
            raise FakturaFeil("Kunne ikke lage PDF! %s" % e)
        pdf.settOrdrelinje(ordre.hentOrdrelinje)
        if blankettType.lower() == "epost":
            res = pdf.lagEpost()
        elif blankettType.lower() == "post":
            res = pdf.lagPost()
        elif blankettType.lower() == "kvittering":
            res = pdf.lagKvittering()
        else:
            raise FakturaFeil("Ugyldig blankett-type: %s" % blankettType)
        if not res:
            raise FakturaFeil("Kunne ikke lage PDF! ('%s')" % spdf.filnavn)

        return pdf

    def skrivUt(self, filnavn: str):
        return fil.vis(filnavn)

    def sendEpost(self, ordre, pdf, tekst=None, transport='auto'):
        if type(transport) == int:
            transport = epost.TRANSPORTMETODER[transport]
        if transport == 'auto':
            transport = self.testEpost()
            if transport is None:
                return False
            self.epostoppsett.transport = transport

        m = getattr(epost, transport)()  # laster riktig transport (smtp/sendmail)
        oppsett = self.epostoppsett
        if transport == 'smtp':
            m.tls(bool(oppsett.smtptls))
            m.settServer(oppsett.smtpserver, oppsett.smtpport)
            if oppsett.smtpbruker: m.auth(oppsett.smtpbruker, oppsett.smtppassord)
        elif transport == 'sendmail':
            m.settSti(oppsett.sendmailsti)
        if oppsett.bcc is not None and len(oppsett.bcc) > 0:
            m.settKopi(oppsett.bcc)
        m.faktura(ordre, pdf, tekst, testmelding=self.produksjonsversjon == False)
        return m.send()

    def testEpost(self, transport='auto'):
        if type(transport) == int:
            transport = epost.TRANSPORTMETODER[transport]
        logging.debug('skal teste transport: %s', transport)
        # finn riktig transport (gmail/smtp/sendmail)
        if not transport in epost.TRANSPORTMETODER:  #ugyldig transport oppgitt
            transport = 'auto'
        if transport == 'auto':
            feil = []
            for mt in epost.TRANSPORTMETODER[1:]:
                try:
                    if self.testEpost(mt):
                        return mt
                except epost.SendeFeil as E:
                    feil += E
            ex = epost.SendeFeil()
            ex.transport = transport
            ex.transportmetoder = epost.TRANSPORTMETODER[:]
            ex.message = ', '.join(feil)
            #return (False, transport, epost.TRANSPORTMETODER)
            raise ex
        logging.debug('tester epost. transport: %s', transport)
        m = getattr(epost, transport)()  # laster riktig transport
        assert m == epost.Epost
        oppsett = self.epostoppsett
        if transport == 'smtp':
            m.tls(bool(oppsett.smtptls))
            m.settServer(oppsett.smtpserver, oppsett.smtpport)
            if oppsett.smtpbruker: m.auth(oppsett.smtpbruker, oppsett.smtppassord)
        elif transport == 'sendmail':
            m.settSti(oppsett.sendmailsti)
        try:
            t = m.test()
        except Exception as inst:
            logging.debug("%s gikk %s", transport, inst.__str__())
            ex = epost.SendeFeil()
            ex.transport = transport
            ex.transportmetoder = epost.TRANSPORTMETODER[:]
            ex.message = inst.__str__()
            raise ex
        else:
            if t:
                logging.debug("%s gikk %s", transport, t)
                return transport
            else:
                return None


def lagDatabase(database: Path, sqlfile: Optional[str] = None):
    "lager databasestruktur. 'database' er filnavn (unicode)"
    try:
        db = sqlite3.connect(database, isolation_level=None)
        return byggDatabase(db, sqlfile)
    except sqlite3.DatabaseError:
        raise
        # hmm, kanskje gammel database?
        dbver = sjekkDatabaseVersjon(database)
        if dbver != sqlite3.sqlite_version_info[0]:
            e = "Databasen din (versjon %s) kan ikke leses av pysqlite, som leser versjon %s" % (dbver, sqlite3.sqlite_version_info[0])
            print("FEIL!", e)
            raise DBVersjonFeil(e)


def byggDatabase(db: sqlite3.Connection, sqlfile: Optional[str] = None):
    "lager databasestruktur. 'db' er et sqlite3.Connection-objekt"
    if sqlfile is not None:
        sql = open(sqlfile).read()
    else:
        sql = str(lesRessurs('sql:faktura.sql'))
    db.executescript(sql)
    db.cursor().execute("INSERT INTO Oppsett (ID, databaseversjon, fakturakatalog) VALUES (1, ?, ?)", (DATABASEVERSJON, '~'))
    db.commit()
    return db


def finnDatabasenavn(databasenavn: str = DATABASENAVN) -> Path:
    """finner et egnet sted for databasefila, enten fra miljøvariabler eller i standard plassering.

    følgende miljøvariabler påvirker denne funksjonen:
    FAKTURADB=navnet eller hele stien til databasefila (eks. firma2.db)
    FAKTURADIR=stien til en katalog databasene skal lagres i (eks. ~/.mittandrefirma)

    også verdien av den interne konstanten PRODUKSJONSVERSJON påvirker returverdien.

    returnerer filnavn som unicode-streng
    """
    db_navn = os.getenv('FAKTURADB')

    if db_navn is not None:
        db = Path(db_navn)
        if not PRODUKSJONSVERSJON or (db.is_file()):
            return db
    if os.getenv('FAKTURADIR') is not None:
        fdir = Path(os.getenv('FAKTURADIR'))
    else:
        #sjekk for utviklermodus
        if not PRODUKSJONSVERSJON:
            return Path(databasenavn)  # returner DATABASENAVN ('faktura.db'?) i samme katalog
        #sjekk for windows
        fdir = Path.home() / "finfaktura"

    if not os.path.exists(fdir):
        os.mkdir(fdir, 0o700)
    return fdir / databasenavn


def kobleTilDatabase(dbnavn: Optional[Path] = None):
    if dbnavn is None:
        dbnavn = finnDatabasenavn()
    logging.debug('skal koble til %s (%s/%s)', dbnavn, repr(dbnavn), type(dbnavn))

    try:
        db = sqlite3.connect(database=dbnavn.absolute(), isolation_level=None)  # isolation_level = None gir autocommit-modus
        logging.debug("Koblet til databasen %s", dbnavn.absolute())
        return db
    except sqlite3.DatabaseError:
        logging.debug("Vi bruker sqlite %s", sqlite3.apilevel)
        dbver = sjekkDatabaseVersjon(dbnavn)
        logging.debug("Databasen er sqlite %s", dbver)
        if sqlite3.apilevel != dbver:
            raise DBVersjonFeil("Databasen er versjon %s, men biblioteket er versjon %s" % (dbver, sqlite3.apilevel))


def sjekkDatabaseVersjon(dbnavn: str):
    """ skiller melllom sqlite 2 og 3. Forventer dbnavn i unicode"""
    #http://marc.10east.com/?l=sqlite-users&m=109382344409938&w=2
    #> It is safe to read the first N bytes in a db file ... ?
    #Yes.  As far as I know, that's the only sure way to determine
    #the version.  Unfortunately, the form of the header changed in
    #version 3, but if you read the first 33 bytes, you'll have an
    #array that you can search for "SQLite 2" or "SQLite format 3".

    try:
        f = open(dbnavn.encode(sys.getfilesystemencoding()))
        magic = f.read(33)
    except IOError:
        return False
    f.close()
    if 'SQLite 2' in magic: return 2
    elif 'SQLite format 3' in magic: return 3
    else: return False


def sikkerhetskopierFil(filnavn: Path):
    """lager sikkerhetskopi av filnavn -> filnavn~

    Forventer filnavn i unicode"""
    logging.debug('skal sikkerhetskopiere %s (altså %s)', repr(filnavn), repr(filnavn))
    assert filnavn.is_file()
    bkpfil = "%s-%s~" % (filnavn, int(time()))
    return shutil.copyfile(filnavn, bkpfil)


def lesRessurs(ressurs: str):
    """Leser en intern QT4-ressurs (qrc) og returnerer den som en QString.

    'ressurs' er på formatet ':/sti/navn', for eksempel ':/sql/faktura.sql'
    """
    from PyQt6 import QtCore
    QtCore.QDir.addSearchPath('sql', '.')
    QtCore.QDir.addSearchPath('pix', './finfaktura/ui/')
    QtCore.QDir.addSearchPath('data', '.')
    f = QtCore.QFile(ressurs)
    if not f.open(QtCore.QIODevice.OpenModeFlag.ReadOnly | QtCore.QIODevice.OpenModeFlag.Text):
        raise IOError("Kunne ikke åpne ressursen '%s'" % ressurs)
    t = QtCore.QTextStream(f)

    s = t.readAll()
    f.close()
    return s


def typeofqt(obj: Any):
    from PyQt6 import QtWidgets
    if isinstance(obj, QtWidgets.QSpinBox): return 'QSpinBox'
    elif isinstance(obj, QtWidgets.QDoubleSpinBox): return 'QDoubleSpinBox'
    elif isinstance(obj, QtWidgets.QLineEdit): return 'QLineEdit'
    elif isinstance(obj, QtWidgets.QTextEdit): return 'QTextEdit'
    elif isinstance(obj, QtWidgets.QPlainTextEdit): return 'QPlainTextEdit'
    elif isinstance(obj, QtWidgets.QHtmlTextEdit): return 'QHtmlTextEdit'
    elif isinstance(obj, QtWidgets.QComboBox): return 'QComboBox'
    return "QWidget"
