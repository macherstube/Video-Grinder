#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##########################################################
# title:  monitor.py
# author: Josias Bruderer
# date:   13.08.2021
# desc:   monitors the whole operation :)
##########################################################

import time
import psutil


class Monitor:

    def __init__(self, config):
        self.states = {
            "cpu": False,
            "ram": False
        }
        self.ready = False
        self.update_data()

    def update_data(self):
        self.ready = False
        self.sysload()
        self.ready = True

    def get_states(self):
        return self.states

    def sysload(self):
        # gives a single float value
        self.states["cpu"] = psutil.cpu_percent()

        # gives an object with many fields
        self.states["ram"] = psutil.virtual_memory().percent
