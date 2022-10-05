import os

from finfaktura.fakturabibliotek import finnDatabasenavn, DATABASENAVN


def test_finnDatabasenavn():
    navn = finnDatabasenavn()

    assert navn == DATABASENAVN, navn

    navn = finnDatabasenavn("min_database.db")
    assert navn == "min_database.db", navn

    os.environ['FAKTURADB'] = "environ_file.db"
    navn = finnDatabasenavn()

    assert navn == "environ_file.db", navn

    del os.environ['FAKTURADB']
