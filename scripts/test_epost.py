#!/usr/bin/env python
# -*- coding: utf-8 -*-

import smtplib, logging

smtpserver = input('smtp server (smtp.gmail.com): ')
if not smtpserver: smtpserver = 'smtp.gmail.com'
smtpport = input('smtp port (587): ')
if not smtpport: smtpport = 587
brukernavn = input('brukernavn: ')
passord = input('passord: ')

s = smtplib.SMTP()
s.set_debuglevel(3)    
try:                       
    s.connect(smtpserver, smtpport)
    s.ehlo()                                 
    s.starttls()                         
    s.ehlo()                             
    s.login(brukernavn, passord)
    print("HURRA")
except Exception as xxx_todo_changeme:
    (e) = xxx_todo_changeme
    logging.exception(e)
    print("HUFFDA")
s.close()


