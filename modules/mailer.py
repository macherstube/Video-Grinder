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
import logging
from datetime import datetime
from email import utils

__MAIL__ = None

class Mailer:

    def __init__(self, config):
        self.config = config

    def send(self, subject, message):
        if self.config["hostname"] != "":
            context = ssl.create_default_context()
            mailcontent = self.prepare_message(subject, message)
            try:
                with smtplib.SMTP_SSL(self.config["hostname"], self.config["port"],
                                      context=context) as server:
                    server.set_debuglevel(1)
                    server.login(self.config["username"], self.config["password"])
                    server.sendmail(self.config["username"],
                                    self.config["receiver"],
                                    mailcontent)
                    server.close()
            except Exception as e:
                logging.error("Failed to send mail via smtp: " + str(e))
                logging.info(mailcontent)

    def prepare_message(self, subject, body):
        message_structure = 'From: %s\nTo: %s\nSubject: %s\nDate: %s\n\n%s' % \
                            (self.config["username"], self.config["receiver"], subject,
                             utils.format_datetime(datetime.now()), body)
        return message_structure
