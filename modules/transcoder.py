#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##########################################################
# title:  transcoder.py
# author: Josias Bruderer
# date:   13.08.2021
# desc:   transcodes files using ffmpeg :)
##########################################################

import time
import ffmpy


class Transcoder:

    def __init__(self, config):
        self.ready = False
