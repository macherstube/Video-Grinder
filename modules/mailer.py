#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##########################################################
# title:  mailer.py
# author: Josias Bruderer
# date:   29.01.2022
# desc:   simple smtp mailer
##########################################################

import smtplib
import ssl
from datetime import datetime
from email import utils

__MAIL__ = None

class Mailer:

    def __init__(self, config):
        self.config = config

    def send(self, subject, message):
        if self.config["hostname"] != "":
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(self.config["hostname"], self.config["port"],
                                  context=context) as server:
                server.set_debuglevel(1)
                server.login(self.config["username"], self.config["password"])
                server.sendmail(self.config["username"],
                                self.config["receiver"],
                                self.prepare_message(subject, message))
                server.close()

    def prepare_message(self, subject, body):
        message_structure = 'From: %s\nTo: %s\nSubject: %s\nDate: %s\n\n%s' % \
                            (self.config["username"], self.config["receiver"], subject,
                             utils.format_datetime(datetime.now()), body)
        return message_structure
