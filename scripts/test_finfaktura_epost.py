#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, smtplib, logging
logging.basicConfig(level=logging.DEBUG)
sys.path.append('../finfaktura')
import epost

smtpserver = input('smtp server (smtp.gmail.com): ')
if not smtpserver: smtpserver = 'smtp.gmail.com'
smtpport = input('smtp port (587): ')
if not smtpport: smtpport = 587
brukernavn = input('brukernavn: ')
passord = input('passord: ')

s = epost.smtp()
s.settServer(smtpserver, smtpport)
s.tls(True)
s.auth(brukernavn, passord)
try:
  if s.test(): print("HURRA")
  else: print("HUFFDA")
except Exception as xxx_todo_changeme:
  (e) = xxx_todo_changeme
  logging.exception(e)
  print("HUFFDA")
