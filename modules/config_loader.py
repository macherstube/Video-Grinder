#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##########################################################
# title:  config_loader.py
# author: Josias Bruderer
# date:   13.08.2021
# desc:   loading config from a json file
##########################################################

import sys
import json
from pathlib import Path


class Cfg:
    def __init__(self, cfg_file):
        self.cfg_file = cfg_file
        self.config = {}
        self.mandatory = ["MODE"]
        self.init()

    def init(self):
        try:
            path = Path(self.cfg_file)
            if path.is_file():
                with open(path) as config_file:
                    self.config = json.load(config_file)

            if len(self.config) == 0:
                raise ValueError("Config file missing or invalid: " + str(path.absolute()))

            for m in self.mandatory:
                if m not in self.config or len(self.config[m]) == 0:
                    raise ValueError("Config file invalid: " + m + " not found or empty in" + str(path.absolute()))

        except Exception as e:
            print("Unexpected error: ", sys.exc_info()[0])
            raise
