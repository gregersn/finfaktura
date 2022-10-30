# -*- coding: utf-8 -*-
###########################################################################
#    Copyright (C) 2005-2009 Håvard Gulldahl
#    <havard@lurtgjort.no>
#
#    Lisens: GPL2
#
# $Id: fakturakomponenter.py 545 2009-04-13 19:45:25Z havard.gulldahl $
###########################################################################

from pathlib import Path
import sys, time, os.path, os
import sqlite3
from tempfile import mkstemp

import logging, subprocess
from typing import Any, Dict, List, Optional

from .fakturafeil import *
from .f60 import F60

PDFVIS = "/usr/bin/xdg-open"


class FakturaKomponent:
    _egenskaper: Dict[str, Any] = {}
    _egenskaperAldriCache: List[str]
    tabellnavn = ""
    _sqlExists = True
    _egenskaperBlob = []

    def __init__(self, db: sqlite3.Connection, Id: Optional[int] = None):
        self.db = db
        self.c = self.db.cursor()
        self._egenskaperAldriCache = []

        if Id is None:
            Id = self.ny_id()
        self._id = Id
        self._egenskaper = self.hent_egenskaper_liste()
        self.hent_egenskaper()

    def __getattr__(self, egenskap: str):
        #logging.debug("__getattr__: %s" % (egenskap))
        if not self._sqlExists:  #tabellen finnes ikke i databasen
            return None
        if egenskap not in self._egenskaper:
            raise AttributeError("%s har ikke egenskapen %s" % (self.__class__, egenskap))
        if egenskap in self._egenskaperAldriCache:
            self.hent_egenskaper()
        #logging.debug("__getattr__:2: %s" % type(self._egenskaper[egenskap]))
        return self._egenskaper[egenskap]

    def __setattr__(self, egenskap: str, verdi: Any):
        if egenskap in self._egenskaper:  # denne egenskapen skal lagres i databasen
            if type(verdi) == bool:
                verdi = int(verdi)  # lagrer bool som int: 0 | 1
            # elif type(verdi) == buffer and len(verdi) == 0:
            #     verdi = ''
            self.oppdater_egenskap(egenskap, verdi)  # oppdater databasen
        self.__dict__[egenskap] = verdi  # oppdater lokalt for objektet

    def hent_egenskaper_liste(self):
        try:
            self.c.execute("SELECT * FROM %s LIMIT 1" % self.tabellnavn)
        except sqlite3.OperationalError:
            raise
        self._egenskaperListe = [z[0] for z in self.c.description]
        r: Dict[str, Any] = {}
        for z in self._egenskaperListe:
            r.update({z: None})


#       logging.debug("hentEgenskaperListe: %s = %s" % (self._id, r))
        return r

    def hent_egenskaper(self):
        if self._id is None:
            return False
        #logging.debug("SELECT * FROM %s WHERE ID=?" % self.tabellnavn, (self._id,))
        self.c.execute("SELECT * FROM %s WHERE ID=?" % self.tabellnavn, (self._id, ))
        r = self.c.fetchone()
        if r is None: raise DBTomFeil('Det finnes ingen %s med ID %s' % (self.tabellnavn, self._id))
        for z in list(self._egenskaper.keys()):
            verdi = None
            try:
                verdi = r[self._egenskaperListe.index(z)]
            except TypeError:
                print(self.tabellnavn, self._id, z, self._egenskaperListe.index(z), r)

            self._egenskaper.update({z: r[self._egenskaperListe.index(z)]})
            self._egenskaper[z] = verdi

    def oppdater_egenskap(self, egenskap: str, verdi: Any):
        _sql = "UPDATE %s SET %s=? WHERE ID=?" % (self.tabellnavn, egenskap)
        logging.debug("%s <= %s, %s", _sql, repr(verdi), self._id)
        self.c.execute(_sql, (verdi, self._id))
        self.db.commit()

    def ny_id(self):
        #       logging.debug("nyId: -> %s <- %s" % (self.tabellnavn, self._IDnavn))
        self.c.execute("INSERT INTO %s (ID) VALUES (NULL)" % self.tabellnavn)
        self.db.commit()
        return self.c.lastrowid

    def helst_desimal(self, d: Any):
        try:
            return float(d)
        except TypeError:
            return 0.0

    @property
    def id(self):
        # TODO: Store 'kunde' in database if it has no id
        return self._id

    @property
    def egenskaper(self):
        return self._egenskaper


class FakturaKunde(FakturaKomponent):
    tabellnavn = "Kunde"

    slettet: int
    navn: str
    kontakperson: str
    adresse: str
    postnummer: int
    poststed: str
    telefon: str
    telefaks: str
    status: str
    epost: str

    def __init__(self, db: sqlite3.Connection, Id: Optional[int] = None):
        FakturaKomponent.__init__(self, db, Id)

    def __str__(self):
        return "%s, %s, kunde # %03i" % (self.navn, self.epost, self._id)

    def __repr__(self):
        return "kunde # %s, egenskaper: %s" % (self._id, self._egenskaper)

    def postadresse(self):
        #if not self.navn or not self.adresse or not self.poststed:
        #raise KundeFeil("Kundeinfo ikke korrekt utfylt")
        e = dict(self._egenskaper)  # lager kopi
        if not e['postnummer'] and not str(e['postnummer']).isdigit(): e['postnummer'] = ''
        else: e['postnummer'] = str(e['postnummer']).zfill(4)
        try:
            if e['kontaktperson']:
                return "%(navn)s \n"\
                    "v/ %(kontaktperson)s \n"\
                    "%(adresse)s \n"\
                    "%(postnummer)s %(poststed)s" % e #(self._egenskaper)
            else:
                return "%(navn)s \n"\
                    "%(adresse)s \n"\
                    "%(postnummer)s %(poststed)s" % e #(self._egenskaper)
        except TypeError:
            raise KundeFeil("Kundeinfo ikke korrekt utfylt")

    def epostadresse(self):
        "Gir en korrekt epostadresse"
        ### XXX: TODO: quote riktig
        return '"%s" <%s>' % (self.navn, self.epost)

    def sett_slettet(self, erSlettet: bool = True):
        logging.debug("sletter kunde %s: %s", self._id, str(erSlettet))
        if erSlettet: self.slettet = int(time.time())
        else: self.slettet = False

    def finn_ordrer(self):
        'Finner alle gyldige ordrer tilhørende denne kunden'
        #Finn alle id-ene først
        self.c.execute('SELECT ID FROM %s WHERE kundeID=? AND kansellert=0 ORDER BY ordredato ASC' % FakturaOrdre.tabellnavn, (self._id, ))
        return [FakturaOrdre(self.db, kunde=self, Id=i[0]) for i in self.c.fetchall()]


class FakturaVare(FakturaKomponent):
    tabellnavn = "Vare"
    slettet: int
    navn: str
    detaljer: str
    enhet: str
    mva: int
    pris: float

    def __str__(self):
        return str("%s: %.2f kr (%s %% mva)" % (self.navn, self.helst_desimal(self.pris), self.mva))

    def __repr__(self):
        return str("%s, vare # %s" % (self.navn, self._id))

    def sett_slettet(self, slettet: bool = True):
        logging.debug("sletter vare? %s", self._id)
        if slettet: self.slettet = int(time.time())
        else: self.slettet = False

    def finn_kjopere(self):
        "Finner hvem som har kjøpt denne varen, returnerer liste av fakturaKunde"
        sql = 'SELECT DISTINCT kundeID FROM Ordrehode INNER JOIN Ordrelinje ON Ordrehode.ID=Ordrelinje.ordrehodeID WHERE kansellert=0 AND vareID=?'
        self.c.execute(sql, (self._id, ))
        return [FakturaKunde(self.db, Id=i[0]) for i in self.c.fetchall()]

    def finn_totalsalg(self):
        'Finner det totale salgsbeløpet (eks mva) for denne varen'
        self.c.execute(
            'SELECT SUM(kvantum*enhetspris) FROM Ordrelinje INNER JOIN Ordrehode ON Ordrelinje.ordrehodeID=Ordrehode.ID WHERE kansellert=0 AND vareID=?',
            (self._id, ))
        try:
            return self.c.fetchone()[0]
        except TypeError:
            return 0.0

    def finn_antall_salg(self):
        'Finner det totale antallet salg denne varen har gjort'
        self.c.execute(
            'SELECT COUNT(*) FROM Ordrelinje INNER JOIN Ordrehode ON Ordrelinje.ordrehodeID=Ordrehode.ID WHERE kansellert=0 AND vareID=?',
            (self._id, ))
        try:
            return self.c.fetchone()[0]
        except TypeError:
            return 0

    def finn_siste_salg(self):
        'Finner det siste salg denne varen har var med i'
        self.c.execute(
            'SELECT Ordrehode.ID FROM Ordrehode INNER JOIN Ordrelinje ON Ordrehode.ID=Ordrelinje.ordrehodeID WHERE kansellert=0 AND vareID=? ORDER BY ordredato DESC LIMIT 1',
            (self._id, ))
        try:
            return FakturaOrdre(self.db, Id=self.c.fetchone()[0])
        except TypeError:
            return None


class FakturaOrdre(FakturaKomponent):
    tabellnavn = "Ordrehode"
    linje: List['FakturaOrdrelinje'] = []
    kundeID: int
    ordredato: int
    forfall: int
    tekst: str
    kansellert: int = 0
    ferdigstilt: int = 1
    betalt: int = 0

    def __init__(self,
                 db: sqlite3.Connection,
                 kunde: Optional[FakturaKunde] = None,
                 Id: Optional[int] = None,
                 firma: Optional['FakturaFirmainfo'] = None,
                 dato: Optional[int] = None,
                 forfall: Optional[int] = None):
        self.linje = []
        if dato is not None:
            self.ordredato = dato
        self.kunde = kunde
        self.firma = firma
        self.ordreforfall = forfall
        FakturaKomponent.__init__(self, db, Id)
        self._egenskaperAldriCache = ['kansellert', 'betalt']
        if Id is not None:
            self.finnVarer()
            self.kunde = FakturaKunde(db, self.kundeID)

    def __str__(self):
        assert self.kunde is not None

        s = "ordre # %04i, utformet til %s den %s" % (self._id, self.kunde.navn,
                                                      time.strftime("%Y-%m-%d %H:%M", time.localtime(self.ordredato)))
        if self.linje:
            s += "\n"
            for ordre in self.linje:
                s += " o #%i: %s \n" % (ordre._id, str(ordre))
        return str(s)

    def ny_id(self):
        assert self.firma is not None
        assert self.kunde is not None
        if not hasattr(self, 'ordredato'):
            self.ordredato = int(time.time())
        if self.ordreforfall is None:
            self.ordreforfall = int(self.ordredato +
                                    3600 * 24 * self.firma.forfall)  # .firma.forfall er hele dager - ganger opp til sekunder
        self.c.execute("INSERT INTO %s (ID, kundeID, ordredato, forfall) VALUES (NULL, ?, ?, ?)" % self.tabellnavn, (
            self.kunde._id,
            self.ordredato,
            self.ordreforfall,
        ))
        self.db.commit()
        return self.c.lastrowid

    def leggTilVare(self, vare: FakturaVare, kvantum: int, pris: float, mva: int):
        ordrelinje = FakturaOrdrelinje(self.db, self, vare, kvantum, pris, mva)
        self.linje.append(ordrelinje)

    def finnVarer(self):
        self.linje = []
        self.c.execute("SELECT ID FROM %s WHERE ordrehodeID=?" % FakturaOrdrelinje.tabellnavn, (self._id, ))
        for linjeID in [x[0] for x in self.c.fetchall()]:
            o = FakturaOrdrelinje(self.db, self, Id=linjeID)
            self.linje.append(o)

    def hentOrdrelinje(self):
        self.finnVarer()
        return self.linje

    def finnPris(self):
        "regner ut fakturabeløpet uten mva"
        if not self.linje: return 0.0
        p = 0.0
        for vare in self.linje:
            p += vare.kvantum * vare.enhetspris
        return p

    def finnMva(self):
        "regner ut mva for fakturaen"
        if not self.linje: return 0.0
        mva = 0.0
        for vare in self.linje:
            mva += vare.kvantum * vare.enhetspris * vare.mva / 100
        return mva

    def settKansellert(self, kansellert: bool = True):
        logging.debug("Ordre #%s er kansellert: %s", self._id, str(kansellert))
        if kansellert:
            self.kansellert = int(time.time())
        else:
            self.kansellert = False

    def betal(self, dato: Optional[int] = None):
        logging.debug("Betaler faktura #%s", self._id)
        if dato is None:
            dato = int(time.time())
        self.betalt = dato

    def fjernBetalt(self):
        self.betalt = 0

    def lagFilnavn(self, katalog: Path, fakturatype: str):
        assert self.kunde is not None
        logging.debug('lagFilnavn: %s <- %s', katalog, fakturatype)
        if not katalog.expanduser().is_dir():
            logging.debug('lagFilnavn: %s er ikke en gyldig katalog', katalog)
            raise FakturaFeil('%s er ikke en gyldig katalog' % katalog)
        n = katalog / ("faktura-%06d-%s-%s-%s.pdf" %
                       (self.ID, fakturatype, self.kunde.navn.replace(" ", "_").replace("/", "_"), time.strftime("%Y-%m-%d")))
        logging.debug('lagFilnavn ble til %s', str(n))
        return n.expanduser()

    def forfalt(self):
        "forfalt() -> Bool. Er fakturaen forfalt (og ikke betalt)?"
        return not self.betalt and time.time() > self.forfall

    def hentSikkerhetskopi(self):
        self.c.execute("SELECT ID FROM %s WHERE ordreID=?" % FakturaSikkerhetskopi.tabellnavn, (self._id, ))
        return FakturaSikkerhetskopi(self.db, Id=self.c.fetchone()[0])


class FakturaOrdrelinje(FakturaKomponent):
    tabellnavn = "Ordrelinje"

    ordrehodeID: int
    vareID: int
    kvantum: int
    mva: int
    tekst: str
    enhetspris: float

    def __init__(self,
                 db: sqlite3.Connection,
                 ordre: FakturaOrdre,
                 vare: Optional[FakturaVare] = None,
                 kvantum: Optional[int] = None,
                 enhetspris: Optional[float] = None,
                 mva: Optional[int] = None,
                 Id: Optional[int] = None):
        self.ordre = ordre
        self.vare = vare
        if Id is None:
            assert self.vare is not None
            c = db.cursor()
            c.execute("INSERT INTO %s (ID, ordrehodeID, vareID, kvantum, enhetspris, mva) VALUES (NULL, ?, ?, ?, ?, ?)" % self.tabellnavn,
                      (self.ordre._id, self.vare._id, kvantum, enhetspris, mva))
            db.commit()
            Id = c.lastrowid
        FakturaKomponent.__init__(self, db, Id)
        if Id is not None:
            self.vare = FakturaVare(db, self.vareID)

    def __str__(self):
        assert self.vare is not None
        return "%s %s %s a kr %2.2f" % (self.kvantum, self.vare.enhet, self.vare.navn, self.enhetspris)

    def __repr__(self):
        assert self.vare is not None
        return "%03d %s: %s %s a kr %2.2f (%s%% mva)" % (self.vare.ID, self.vare.navn, self.kvantum, self.vare.enhet, self.enhetspris,
                                                         self.mva)

    def ny_id(self):
        pass

    def detaljertBeskrivelse(self):
        assert self.vare is not None
        return str("%03d %s: %s %s a kr %2.2f (%s%% mva)" %
                   (self.vare.ID, self.vare.navn, self.kvantum, self.vare.enhet, self.enhetspris, self.mva))


class FakturaFirmainfo(FakturaKomponent):
    tabellnavn = "Firma"
    _id = 1
    _egenskaperAldriCache = []

    firmanavn: str
    organisasjonsnummer: str
    kontaktperson: str
    epost: str
    adresse: str
    postnummer: Optional[int]
    poststed: str
    telefon: Optional[str]
    mobil: Optional[str]
    telefaks: Optional[str]
    kontonummer: Optional[str]
    vilkar: str
    mva: int
    forfall: int
    logo: Any
    www: str

    def __init__(self, db: sqlite3.Connection):
        self.db = db
        self.c = self.db.cursor()

        self._egenskaper = self.hent_egenskaper_liste()
        try:
            self.hent_egenskaper()
        except DBTomFeil:
            self.lagFirma()
            self._egenskaper = self.hent_egenskaper_liste()
            self.hent_egenskaper()

    def __str__(self):
        return """
      == FIRMA: %(firmanavn)s ==
      Kontakt : %(kontaktperson)s
      Adresse : %(adresse)s, %(postnummer)04i %(poststed)s
      Konto   : %(kontonummer)011i
      Org.nr  : %(organisasjonsnummer)s
      """ % (self._egenskaper)

    #def nyId(self):
    #pass

    def lagFirma(self):
        logging.debug("Lager firma")
        nyFirmanavn = "Fryktelig fint firma"
        nyMva = 25  #prosent
        nyForfall = 21  #dager
        self.c.execute("INSERT INTO %s (ID, firmanavn, mva, forfall) VALUES (?,?,?,?)" % self.tabellnavn,
                       (self._id, nyFirmanavn, nyMva, nyForfall))

        self.db.commit()

    def postadresse(self):
        return "%(firmanavn)s \n"\
               "v/%(kontaktperson)s \n"\
               "%(adresse)s \n"\
               "%(postnummer)04i %(poststed)s" % (self._egenskaper)

    def sjekkData(self):
        sjekk = ["firmanavn", "kontaktperson", "adresse", "postnummer", "poststed", "kontonummer", "epost"]
        mangler = [felt for felt in sjekk if not getattr(self, felt)]
        if mangler:
            raise FirmainfoFeil("Følgende felt er ikke fylt ut: %s" % ", ".join(mangler))


class FakturaOppsett(FakturaKomponent):
    tabellnavn = "Oppsett"
    _id = 1

    databaseversion: float
    fakturakatalog: str
    skrivutpdf: str = ""
    vispdf: str = ""

    def __init__(self, db: sqlite3.Connection, versjonsjekk: bool = True, apiversjon: Optional[float] = None):

        self.apiversjon = apiversjon
        c = db.cursor()
        datastrukturer = [
            FakturaFirmainfo, FakturaKunde, FakturaVare, FakturaOrdre, FakturaOrdrelinje, FakturaOppsett, FakturaSikkerhetskopi,
            FakturaEpost
        ]
        mangler: List[Any] = []
        for obj in datastrukturer:
            try:
                c.execute(f"SELECT * FROM {obj.tabellnavn} LIMIT 1")
            except sqlite3.DatabaseError:
                # db mangler eller er korrupt
                # for å finne ut om det er en gammel versjon
                # sparer vi på tabellene som mangler og sammenligner
                # når vi er ferdige
                mangler.append(obj)
        # hvis alle strukturene mangler, er det en tom (ny) fil
        if datastrukturer == mangler:
            raise DBNyFeil("Databasen er ikke bygget opp")
        elif mangler:  #noen av strukturene mangler, dette er en gammel fil
            if versjonsjekk:
                raise DBGammelFeil("Databasen er gammel eller korrupt, følgende felt mangler: %s" %
                                   ",".join([o.tabellnavn for o in mangler]))

        try:
            FakturaKomponent.__init__(self, db, Id=self._id)
        except DBTomFeil:
            # finner ikke oppsett. Ny, tom database
            sql = "INSERT INTO %s (ID, databaseversjon, fakturakatalog) VALUES (?,?,?)" % self.tabellnavn

            c.execute(sql, (
                self._id,
                self.apiversjon,
                os.getenv('HOME'),
            ))
            db.commit()
            FakturaKomponent.__init__(self, db, Id=self._id)
        except sqlite3.DatabaseError:
            # tabellen finnes ikke
            self._sqlExists = False
            if versjonsjekk:
                raise DBGammelFeil("Databasen mangler tabellen '%s'" % self.tabellnavn)

        if not versjonsjekk: return

        logging.debug("sjekker versjon")
        logging.debug("arkivet er %s, siste er %s", self.databaseversjon, self.apiversjon)
        if self.databaseversjon != self.apiversjon:
            raise DBGammelFeil("Databasen er versjon %s og må oppgraderes til %s" % (self.databaseversjon, self.apiversjon))

    def ny_id(self):
        pass

    """
    TODO: Remove?
    def migrerDatabase(self, nydb, sqlFil):
        db = lagDatabase(nydb, sqlFil)
        # hva nå?
    """

    def hentVersjon(self):
        if not self._sqlExists:  #arbeider med for gammel versjon til at tabellen finnes
            return None
        try:
            return self.databaseversjon
        except AttributeError:
            return None  #gammel databaselayout


class FakturaSikkerhetskopi(FakturaKomponent):
    tabellnavn = "Sikkerhetskopi"
    ordreID: int
    dato: int
    data: Optional['pdfType']

    def __init__(self, db: sqlite3.Connection, ordre: Optional[FakturaOrdre] = None, Id: Optional[int] = None):
        self.dato = int(time.time())
        if ordre is not None:
            self.ordre = ordre
            c = db.cursor()
            c.execute("INSERT INTO %s (ID, ordreID, dato) VALUES (NULL, ?, ?)" % self.tabellnavn, (self.ordre._id, self.dato))
            db.commit()
            Id = c.lastrowid
            FakturaKomponent.__init__(self, db, Id)
            spdf = F60(filnavn=None)
            spdf.settFakturainfo(ordre._id, ordre.ordredato, ordre.forfall, ordre.tekst)
            spdf.settFirmainfo(ordre.firma._egenskaper)
            try:
                spdf.settKundeinfo(ordre.kunde._id, ordre.kunde.postadresse())
            except KundeFeil as e:
                raise FakturaFeil("Kunne ikke lage PDF! %s" % e)

            spdf.settOrdrelinje(ordre.hentOrdrelinje)
            res = spdf.lagKvittering()
            if not res:
                raise FakturaFeil("Kunne ikke lage PDF! ('%s')" % spdf.filnavn)

            self.data = pdfType(spdf.data())

        elif Id is not None:
            FakturaKomponent.__init__(self, db, Id)

    def ordre(self):
        # TODO: What is the purpose here, Should this be a property instead?
        return FakturaOrdre(self.db, Id=self.ordreID)

    def hent_egenskaper(self):
        if self._id is None:
            return False
        sql = "SELECT ID, ordreID, dato, CAST(data as blob) FROM %s WHERE ID=?" % self.tabellnavn
        self.c.execute(sql, (self._id, ))
        r = self.c.fetchone()
        self._egenskaper['ordreID'] = r[1]
        self._egenskaper['dato'] = r[2]
        self._egenskaper['data'] = pdfType(r[3])

    def lag_fil(self):
        f, filnavn = mkstemp('.pdf', 'sikkerhetsfaktura')
        #fil = open(filnavn, "wb")
        #fil.write(str(self.data))
        #fil.close()
        os.write(f, str(self.data))
        os.close(f)
        return filnavn

    def vis(self, program: str = PDFVIS):
        "Dersom program inneholder %s vil den bli erstattet med filnavnet, ellers lagt til etter program"
        logging.debug('Åpner sikkerhetskopi #%i med programmet "%s"', self._id, program)
        p = program.encode(sys.getfilesystemencoding())  # subprocess.call på windows takler ikke unicode!
        f = self.lag_fil().encode(sys.getfilesystemencoding())
        if '%s' in program:
            command = (p % f).split(' ')
        else:
            command = (p, f)
        logging.debug('kjører kommando: %s', command)
        subprocess.call(command)


class FakturaEpost(FakturaKomponent):
    tabellnavn = "Epost"
    _id = 1

    bcc: str
    transport: int
    gmailbruker: str
    gmailpassord: str
    smtpserver: str
    smtpport: int
    smtptls: bool
    smtpauth: bool
    smtpbruker: str
    smtppassord: str
    sendmailsti: str

    def __init__(self, db: sqlite3.Connection):
        self.db = db
        try:
            FakturaKomponent.__init__(self, db, Id=self._id)
        except DBTomFeil:
            #ikke brukt før
            self.c.execute("INSERT INTO Epost (ID) VALUES (1)")
            self.db.commit()
            FakturaKomponent.__init__(self, db, Id=self._id)

    def ny_id(self):
        pass


class pdfType:
    'Egen type for å holde pdf (f.eks. sikkerhetskopi)'

    def __init__(self, data: Any):
        self.data = data

    #def _quote(self):
    #'Returnerer streng som kan puttes rett inn i sqlite3. Kalles internt av pysqlite'
    #if not self.data: return "''"
    #import sqlite3
    #return str(sqlite3.Binary(self.data))

    def __str__(self):
        return str(self.data)

    def __conform__(self, protocol: sqlite3.PrepareProtocol):
        if protocol is sqlite3.PrepareProtocol:
            return sqlite3.Binary(self.data)
