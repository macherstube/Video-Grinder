#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##########################################################
# title:  organizer.py
# author: Josias Bruderer
# date:   13.08.2021
# desc:   organize transcoded and current media
##########################################################

from pathlib import Path
import threading


def threaded(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()
    return wrapper

class Organizer:

    def __init__(self, config):
        self.ready = False
        self.config = config
        self.createTranscoderCache()

    def createTranscoderCache(self):
        Path(self.config["transcoderCache"]).mkdir(parents=True, exist_ok=True)
