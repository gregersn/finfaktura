@ECHO OFF
SET RESSURSER="faktura.qrc"
SET UIDIR="finfaktura\ui"

ECHO Kompilerer ressurser...
pyrcc6 -o %UIDIR%\faktura_rc.py faktura.qrc

ECHO Kompilerer grensesnitt...

ECHO faktura.ui

CMD /C pyuic6 -o %UIDIR%\faktura_ui.py %UIDIR%\faktura.ui

ECHO finfaktura_oppsett.ui

CMD /C pyuic6 -o %UIDIR%\finfaktura_oppsett_ui.py %UIDIR%\finfaktura_oppsett.ui

ECHO firmainfo.ui

CMD /C pyuic6 -o %UIDIR%\firmainfo_ui.py %UIDIR%\firmainfo.ui

ECHO sendepost.ui

CMD /C pyuic6 -o %UIDIR%\sendepost_ui.py %UIDIR%\sendepost.ui

ECHO epost.ui

CMD /C pyuic6 -o %UIDIR%\epost_ui.py %UIDIR%\epost.ui


