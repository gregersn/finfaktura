#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""cli-magi"""
###########################################################################
#    Copyright (C) 2005-2009 Håvard Gulldahl
#    <havard@lurtgjort.no>
#
#    Lisens: GPL2
#
# $Id$
###########################################################################

import os
from pathlib import Path
import sys
from typing import Any, List, Optional
from .fakturabibliotek import FakturaBibliotek, kobleTilDatabase


def cli_faktura():
    db = kobleTilDatabase()
    assert db is not None
    bib = FakturaBibliotek(db)
    kunder = bib.hentKunder()
    kunde = CLIListe(kunder, "velg kunde: ")
    print("kunde: ", str(kunde))
    varer = bib.hentVarer()
    vare = CLIListe(varer, "velg vare: ")
    antall = ""
    while not antall.isdigit():
        antall = CLIInput("antall %s: " % vare.enhet)
    antall = int(antall)
    tekst = CLIInput("Fakturatekst: ")
    mva = vare.mva * vare.pris * antall / 100
    sum = vare.pris * antall + mva
    print("""STEMMER DETTE?
    =====
    Kunde: %s
    Vare: %s %s %s
    Tekst: %s
    SUM: %.2f kr (derav mva: %.2f)
    ===== """ % (kunde, antall, vare.enhet, vare, tekst, sum, mva))
    ja = CLIInput("NEI/ja (Enter for å avbryte): ")
    if not (len(ja) > 0 and ja.strip().lower()[0] == "j"):
        return False
    firma = bib.firmainfo()
    ordre = bib.nyOrdre(kunde)
    ordre.tekst = tekst
    ordre.leggTilVare(vare, antall, vare.pris, vare.mva)
    bib.lagSikkerhetskopi(ordre)

    fakturanavn = ordre.lagFilnavn(Path(bib.oppsett.fakturakatalog), fakturatype="epost")

    try:
        pdf = bib.lagPDF(ordre, "epost", fakturanavn)
    except FakturaFeil as xxx_todo_changeme:
        (E) = xxx_todo_changeme
        print("OUCH! Kunne ikke lage PDF! Årsak: %s" % E)
    except KundeFeil as xxx_todo_changeme1:
        (E) = xxx_todo_changeme1
        print("OUCH! Kunne ikke lage PDF! Årsak: %s" % E)

    print("Lagde pdf: %s" % pdf.filnavn)
    db.close()


def CLIenkoding():
    "Prøver å finne den gjeldende enkodingen på input"
    for z in ('LANG', 'LC_CTYPE', 'LC_ALL'):
        if z in os.environ:
            k = os.environ[z].lower()
            if k.find('utf8') != -1 or k.find('utf-8') != -1: return 'utf8'
    return 'latin1'


def CLIListe(liste: List[Any], tekst: Optional[str] = None):
    if not tekst:
        tekst = f"velg blant {len(liste)}:"
    try:
        print(f"velg fra liste ({len(liste)} valg):")
        i = 1
        for l in liste:
            print("\t", i, str(l))
            i += 1
        ret = input(tekst)
    except EOFError:
        return CLIListe(liste)
    except KeyboardInterrupt:
        print()
        sys.exit(1)
    else:
        if (not ret.isdigit()) or (int(ret) < 1 or int(ret) > len(liste)):
            return CLIListe(liste, "det er ikke særlig gyldig, sjø!")
        else:
            idx = int(ret) - 1
            return liste[idx]


def CLIInput(tekst: str) -> str:
    try:
        ret = input(tekst)
    except EOFError:
        return CLIInput(tekst)
    except KeyboardInterrupt:
        print()
        sys.exit(1)
    else:
        return ret
