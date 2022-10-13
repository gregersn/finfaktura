#!/usr/bin/env python
# -*- coding:utf8 -*-
###########################################################################
#    Copyright (C) 2005-2009 Håvard Gulldahl
#    <havard@lurtgjort.no>
#
#    Lisens: GPL2
#
# $Id$
###########################################################################

from io import BufferedReader
from pathlib import Path
import os, os.path, logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from email.header import Header
import socket
from typing import Any, List, Literal, Optional, Tuple, Union

from finfaktura.fakturakomponenter import fakturaOrdre

TRANSPORTMETODER = ['auto', 'smtp', 'sendmail']


class SendeFeil(Exception):
    pass


class UgyldigVerdi(Exception):
    pass


class IkkeImplementert(Exception):
    pass


class Epost:

    charset = 'iso-8859-15'  # epostens tegnsett
    kopi: Optional[str] = None
    brukernavn: str
    passord: str
    testmelding: bool = True
    vedlegg: List[Tuple[str, Any]] = []
    transport: str

    def faktura(self,
                ordre: fakturaOrdre,
                pdfFilnavn: str,
                tekst: Optional[str] = None,
                fra: Optional[str] = None,
                testmelding: bool = False):
        if not type(pdfFilnavn) in (str, ):
            raise UgyldigVerdi('pdfFilnavn skal være tekst (ikke "%s")' % type(pdfFilnavn))
        self.ordre = ordre
        self.pdfFilnavn = pdfFilnavn
        assert ordre.firma is not None
        if fra is None:
            fra = ordre.firma.epost
        self.fra = fra
        assert ordre.kunde is not None
        self.til = ordre.kunde.epost
        self.tittel = "Epostfaktura fra %s: '%s' (#%i)" % (ordre.firma.firmanavn, self.kutt(ordre.tekst), ordre.ID)
        if tekst is None:
            tekst = 'Vedlagt følger epostfaktura #%i:\n\n%s\n\n-- \n%s\n%s' % (ordre.ID, ordre.tekst, ordre.firma, ordre.firma.vilkar)
        self.tekst = tekst
        self.testmelding = testmelding
        if self.testmelding:  # vi er i utviklingsmodus, skift tittel
            self.tittel = "TESTFAKTURA " + self.tittel

    def mimemelding(self):
        m = MIMEMultipart()
        m['Subject'] = Header(self.tittel, self.charset)
        assert self.ordre.firma is not None
        n = self.ordre.firma.firmanavn.replace(';', ' ').replace(',', ' ')
        m['From'] = '"%s" <%s>' % (Header(n, self.charset), self.fra)
        #m['To'] = '"%s" <%s>' % (Header(self.ordre.kunde.navn, self.charset), self.til)
        m['To'] = self.til  #'"%s" <%s>' % (Header(self.ordre.kunde.navn, self.charset), self.til)
        m.preamble = 'You will not see this in a MIME-aware mail reader.\n'
        # To guarantee the message ends with a newline
        m.epilogue = ''

        # Legg til tekstlig informasjon
        t = MIMEText(self.tekst, 'plain', self.charset)
        m.attach(t)

        # Legg til fakturaen
        b = MIMEBase('application', 'x-pdf')
        _filename = Header('%s-%i.pdf' % (self.ordre.firma.firmanavn, self.ordre.ID), self.charset)
        b.add_header('Content-Disposition', 'attachment', filename=_filename.encode())  # legg til filnavn
        m.attach(b)
        fp = open(self.pdfFilnavn, 'rb')
        b.set_payload(fp.read())  # les inn fakturaen
        fp.close()
        encoders.encode_base64(b)  #base64 encode subpart

        # Legg til vedlegg
        for filnavn, vedlegg in self.vedlegg:
            v = MIMEBase('application', 'octet-stream')
            _filename = Header(filnavn, self.charset)
            v.add_header('Content-Disposition', 'attachment', filename=_filename.encode())  # legg til filnavn
            m.attach(v)
            v.set_payload(vedlegg)
            encoders.encode_base64(v)  #base64 encode subpart

        return m

    def auth(self, brukernavn: str, passord: str):
        if not type(brukernavn) in (str, ):
            raise UgyldigVerdi('Brukernavn skal være tekst (ikke "%s")' % type(brukernavn))
        if not type(passord) in (str, ):
            raise UgyldigVerdi('Passord skal være tekst (ikke "%s")' % type(passord))
        self._auth = True
        self.brukernavn = brukernavn
        self.passord = passord

    def send(self):
        return True

    def test(self):
        return True

    def kutt(self, s: str, l: int = 30):
        if len(s) < l: return s
        return s[0:l] + "..."

    def settKopi(self, s: str):
        # setter BCC-kopi til s
        if not type(s) in (str, ):
            raise UgyldigVerdi('Epostadresse skal være tekst (ikke "%s")' % type(s))
        # sjekk at s er en gyldig epostadresse
        if not '@' in s:
            raise UgyldigVerdi('Denne epostadressen er ikke gyldig: %s' % s)
        self.kopi = s

    def nyttVedlegg(self, f: Union[str, BufferedReader]):
        "Legg til vedlegg. `f' kan være et filnavn eller et file()-objekt"
        if isinstance(f, str) and Path(f).is_file():
            _f = open(f, 'rb')
            self.vedlegg.append((f, _f.read()))
            _f.close()
            return True
        elif isinstance(f, BufferedReader):
            self.vedlegg.append(('noname', f.read()))
            return True
        else:
            return False


class SMTP(Epost):
    smtpserver = 'localhost'
    smtpport = 25
    _tls = False
    _auth = False

    def settServer(self, smtpserver: str, port: int = 25):
        if not type(smtpserver) in (str, ):
            raise UgyldigVerdi('smtpserver skal være tekst (ikke "%s")' % type(smtpserver))
        if not type(port) == int:
            raise UgyldigVerdi('port skal være et heltall (ikke "%s")' % type(port))
        self.smtpserver = str(smtpserver)
        self.smtpport = int(port)

    def tls(self, _bool: bool):
        if not type(_bool) == bool:
            raise UgyldigVerdi('Verdien skal være True eller False (ikke "%s")' % type(_bool))
        self._tls = _bool

    def test(self):
        s = smtplib.SMTP()
        if self.testmelding:  #debug
            s.set_debuglevel(1)
        s.connect(self.smtpserver, self.smtpport)
        s.ehlo()
        if self._tls:
            s.starttls()
            s.ehlo()
        if self._auth:
            s.login(self.brukernavn, self.passord)
        s.close()
        return True

    def send(self):
        s = smtplib.SMTP()
        if self.testmelding:  #debug
            s.set_debuglevel(1)
        try:
            s.connect(self.smtpserver, self.smtpport)
            s.ehlo()
            if self._tls:
                s.starttls()
                s.ehlo()
            if self._auth:
                s.login(self.brukernavn, self.passord)
        except socket.error as E:
            raise SendeFeil(E)
        except:
            raise
        mottakere = [
            self.til,
        ]
        if self.kopi: mottakere.append(self.kopi)  # sender kopi til oss selv (BCC)
        logging.debug("mottaker: %s", mottakere)
        logging.debug("fra: %s (%s)", self.fra, type(self.fra))
        res = s.sendmail(self.fra, mottakere, self.mimemelding().as_string())
        s.close()
        if len(res) > 0:
            ### Fra help(smtplib):
            # >>> s.sendmail("me@my.org",tolist,msg)
            #|       { "three@three.org" : ( 550 ,"User unknown" ) }
            #|
            #|      In the above example, the message was accepted for delivery to three
            #|      of the four addresses, and one was rejected, with the error code
            #|      550.  If all addresses are accepted, then the method will return an
            #|      empty dictionary.

            feil = ["%s: %s" % (a, res[a][1]) for a in list(res.keys())]
            raise SendeFeil('Sendingen feilet for disse adressene:\n%s' % "\n".join(feil))
        return True


class Sendmail(Epost):
    bin = '/usr/lib/sendmail'
    _auth = False

    def settSti(self, sti: str):
        if not type(sti) in (str, ):
            raise UgyldigVerdi('sti skal være tekst (ikke "%s")' % type(sti))
        self.bin = sti

    def test(self):
        import os.path as p
        real = p.realpath(self.bin)
        logging.debug("fullstendig sti: %s", real)
        if not (p.exists(real) and p.isfile(real)):  # er dette tilstrekkelig?
            raise SendeFeil('%s er ikke en gyldig sendmail-kommando' % self.bin)
        return True

    def send(self):
        # ssmtp opsjoner:
        #-4     Forces ssmtp to use IPv4 addresses only.
        #-6     Forces ssmtp to use IPv6 addresses only.
        #-auusername
        #Specifies username for SMTP authentication.
        #-appassword
        #Specifies password for SMTP authentication.
        #-ammechanism
        #Specifies mechanism for SMTP authentication. (Only LOGIN and CRAM-MD5)
        # XXX TODO: Hvordan gjøre auth uavhengig av sendmail-implementasjon?
        kmd = "%s %s" % (self.bin, self.til)
        if self.kopi: kmd += " %s" % self.kopi  # kopi til oss selv (BCC)
        logging.debug("starter prosess: %s", kmd)
        raise NotImplementedError("Replace popen4")
        inn, ut = os.popen4(kmd)
        try:
            inn.write(self.mimemelding().as_string())
            r = inn.close()
        except:
            raise SendeFeil('Sendingen feilet fordi:\n' + ut.read())
        #i = inn.close()
        u = ut.close()
        logging.info('sendmail er avsluttet; %s U %s' % (r, u))
        return True


class Dump(Epost):

    def send(self):
        print(self.mimemelding().as_string())
        return True

    def test(self):
        return self.send()
