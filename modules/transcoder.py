#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##########################################################
# title:  transcoder.py
# author: Josias Bruderer
# date:   13.08.2021
# desc:   transcodes files using ffmpeg :)
##########################################################
import shutil
import subprocess
import threading
from ffmpy import FFmpeg, FFRuntimeError
from pathlib import Path


def threaded(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()

    return wrapper


class Transcoder:

    def __init__(self, config):
        self.config = config
        self.exit_code = -1
        self.file = None
        self.ready = True

    @threaded
    def transcode(self, file):
        self.ready = False
        self.file = file
        path = Path(file.locations[0])
        if not path.is_file():
            if self.config["MODE"] == "development" or self.config["MODE"] == "debug":
                print("No such file or directory: ", str(path))
            self.exit_code = 404
            self.ready = True
            return
        cacheDir = Path(self.config["transcoderCache"]).joinpath(str(file.ratingKey))
        cacheDir.mkdir(parents=True, exist_ok=True)
        cachePath = cacheDir.joinpath(str(path.stem) + "_h265." + self.config["targetContainer"])
        hwaccel = str("-hwaccel " + self.config["transcoderHWaccel"]) if self.config["transcoderHWaccel"] != "False" else ""
        ff = FFmpeg(
            inputs={str(path): str("-y " + hwaccel)},
            outputs={str(cachePath): str("-c:v " + self.config["targetCodec"] + " " + self.config["targetSettings"])}
        )
        if self.config["MODE"] == "development" or self.config["MODE"] == "debug":
            print("Trying to transcode: ", str(path))
            print(ff.cmd)

        try:
            if self.config["readonly"] == "False":
                stdout, stderr = ff.run(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except FFRuntimeError as ffe:
            # After receiving SIGINT ffmpeg has a 255 exit code
            if ffe.exit_code == 255:
                self.exit_code = 255
                pass
            else:
                if cachePath.parent.is_dir():
                    if self.config["readonly"] == "False":
                        shutil.rmtree(cachePath.parent)
                if "No such file or directory" in str(ffe.stderr):
                    self.exit_code = 404
                else:
                    self.exit_code = 500
                raise ValueError("An unexpected FFRuntimeError occurred: " "{}".format(ffe))
        except KeyboardInterrupt:
            if cachePath.parent.is_dir():
                if self.config["readonly"] == "False":
                    shutil.rmtree(cachePath.parent)
            self.exit_code = 255
            pass  # Do nothing if voluntary interruption
        finally:
            self.ready = True

        if self.config["MODE"] == "development" or self.config["MODE"] == "debug":
            print("Successfully transcoded: ", str(cachePath))
        self.exit_code = 0
