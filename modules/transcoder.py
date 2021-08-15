#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##########################################################
# title:  transcoder.py
# author: Josias Bruderer
# date:   13.08.2021
# desc:   transcodes files using ffmpeg :)
##########################################################

import time
import threading
from ffmpy import FFmpeg
from pathlib import Path


def threaded(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()

    return wrapper


class Transcoder:

    def __init__(self, config):
        self.config = config
        self.ready = True

    @threaded
    def transcode(self, file):
        self.ready = False
        path = Path(file.locations[0])
        cachePath = Path(self.config["transcoderCache"]).joinpath(str(path.stem) + ".mkv")
        print("fake transcoding start: ", path)
        ff = FFmpeg(
            inputs={str(path): "-hwaccel cuda"},
            outputs={str(cachePath): "-c:v hevc_nvenc"}
        )
        print(ff.cmd)
        ff.run()

        time.sleep(5)
        print("fake transcoding end: ", file)
        self.ready = True
