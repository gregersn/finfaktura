#!/usr/bin/env python3 -d
###########################################################################
#    Copyright (C) 2005-2008 Håvard Gulldahl
#    <havard@lurtgjort.no>
#
#    Lisens: GPL2
#
# $Id$
###########################################################################
"""Exceptions for Invoice."""


class FakturaFeil(Exception):
    """Error in invoice."""


class KundeFeil(Exception):
    """Error with customer."""


class DBKorruptFeil(Exception):
    """Database corrupt."""


class DBGammelFeil(Exception):
    """Database is outdated."""


class DBNyFeil(Exception):
    """Database is too new."""


class DBTomFeil(Exception):
    """Database is empty."""


class DBVersjonFeil(Exception):
    """Database version is wrong."""


class FirmainfoFeil(Exception):
    """Error in information about company."""


class SikkerhetskopiFeil(Exception):
    """Error in backup."""


class PDFFeil(Exception):
    """Error in PDF."""


class RessurserManglerFeil(Exception):
    """Resource is missing."""


class InstallasjonsFeil(Exception):
    """Installation error."""
