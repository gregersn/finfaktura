# -*- coding:utf-8 -*-
"""Regne økonomi"""
###########################################################################
#    Copyright (C) 2005-2009 Håvard Gulldahl
#    <havard@lurtgjort.no>
#
#    Lisens: GPL2
#
# $Id$
###########################################################################

import logging
import sqlite3
from typing import List, Optional
from .fakturakomponenter import fakturaKunde, fakturaOrdre, fakturaVare


class OrdreHenter:
    """Hent ordre fra databasen."""
    begrens = []
    varer = []
    vare = False
    sorter = None
    antall = None

    def __init__(self, db: sqlite3.Connection):
        self.db = db
        self.c = db.cursor()
        self.begrens: List[str] = []
        self.varer: List[int] = []
        self.vare: bool = False
        self.sorter = None
        self.antall: Optional[int] = None

    def begrensDato(self, fraEpoch: Optional[int] = None, tilEpoch: Optional[int] = None):
        if fraEpoch is not None:
            self.begrens.append(f" ordredato > {fraEpoch}")
        if tilEpoch is not None:
            self.begrens.append(f" ordredato < {tilEpoch}")

    def begrensKunde(self, kunde: fakturaKunde):
        self.begrens.append(f" kundeID = {kunde.id} ")

    def begrensVare(self, vare: fakturaVare):
        if vare.id:
            self.vare = True
            self.varer.append(vare.id)

    def begrensAntall(self, antall: int):
        self.antall = antall

    def visKansellerte(self, vis: bool):
        if not vis:
            self.begrens.append(" kansellert = 0 ")

    def visUbetalte(self, vis: bool):
        if not vis:
            self.begrens.append(" betalt != 0 ")

    def sorterEtter(self, kolonne: str):
        s = {'dato': 'ordredato', 'kunde': 'kundeID', 'vare': 'vareID'}
        self.sorter = f" ORDER BY {s[kolonne]} "
        if kolonne == 'vare':
            self.vare = True

    def hentOrdrer(self):
        self.c.execute(self._sql())
        return [fakturaOrdre(self.db, Id=z[0]) for z in self.c.fetchall()]

    def _sql(self):
        s = f"SELECT Ordrehode.ID FROM {fakturaOrdre.tabellnavn}"
        if self.vare:
            # SELECT Ordrehode.ID FROM Ordrehode LEFT OUTER JOIN Ordrelinje ON Ordrehode.ID=Ordrelinje.ordrehodeID WHERE vareID=3;
            s += " LEFT OUTER JOIN Ordrelinje ON Ordrehode.ID=Ordrelinje.ordrehodeID "
            #s += join(vareID=%i " % self.
            for v in self.varer:
                self.begrens.append(f" vareID={v} ")
        if self.begrens:
            s += " WHERE " + " AND ".join(self.begrens)
        if self.sorter:
            s += self.sorter
        if self.antall:
            s += f" LIMIT {self.antall} "
        logging.debug(s)
        return s
