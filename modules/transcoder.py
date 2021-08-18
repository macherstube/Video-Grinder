#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##########################################################
# title:  transcoder.py
# author: Josias Bruderer
# date:   16.08.2021
# desc:   transcodes files using ffmpeg :)
##########################################################

import logging
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
        # set readiness to False to avoid conflicts
        self.ready = False
        self.file = file
        # cannot process files with more than one location
        if len(file.locations) > 1:
            logging.warning("transcoder: more than one file found - cannot handle that. :-( :" + str(file))
            self.exit_code = 405
            self.ready = True
            return
        # get path of file and check if file exists
        path = Path(file.locations[0])
        if "fakeFileSystem" in self.config and len(self.config["fakeFileSystem"]) > 0:
            path = Path(str(path).replace(self.config["fakeFileSystem"]["search"][0],
                                          self.config["fakeFileSystem"]["replace"][0])
                        .replace(self.config["fakeFileSystem"]["search"][1],
                                 self.config["fakeFileSystem"]["replace"][1]))
        if not path.is_file():
            logging.warning("transcoder: No such file or directory: " + str(path))
            self.exit_code = 404
            self.ready = True
            return
        # get path of cache directory and create if not existing
        cacheDir = Path(self.config["transcoderCache"]).joinpath(str(file.ratingKey))
        cacheDir.mkdir(parents=True, exist_ok=True)
        # get target path to transcode to
        cachePath = cacheDir.joinpath(str(path.stem) + "." + self.config["targetContainer"])
        # build transcode string
        hwaccel = str("-hwaccel " + self.config["transcoderHWaccel"]) if self.config["transcoderHWaccel"] != "False" else ""
        # create ffmpeg request
        ff = FFmpeg(
            inputs={str(path): str("-y " + hwaccel)},
            outputs={str(cachePath): str("-c:v " + self.config["targetVideoCodec"] + " "
                                         + self.config["targetVideoSettings"]) + " "
                                         + "-c:a " + self.config["targetAudioCodec"] + " "
                                         + self.config["targetAudioSettings"]}
        )
        logging.info("transcoder: Trying to transcode: " + str(path))
        logging.debug("transcoder: " + ff.cmd)

        successfully = True
        try:
            # make sure to only change file when not readonly
            if self.config["readonly"] == "False":
                # run transcode command
                stdout, stderr = ff.run(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except FFRuntimeError as ffe:
            successfully = False
            # After receiving SIGINT ffmpeg has a 255 exit code
            if ffe.exit_code == 255:
                self.exit_code = 255
            else:
                # if failed, clean up caching directory and broken files
                if cachePath.parent.is_dir():
                    if self.config["readonly"] == "False":
                        shutil.rmtree(cachePath.parent)
                if "No such file or directory" in str(ffe.stderr):
                    # not found error
                    self.exit_code = 404
                else:
                    # undefined error
                    self.exit_code = 500
                logging.error("transcoder: An FFRuntimeError occurred in: " "{}".format(ffe))
        except KeyboardInterrupt:
            successfully = False
            if cachePath.parent.is_dir():
                if self.config["readonly"] == "False":
                    shutil.rmtree(cachePath.parent)
            self.exit_code = 255
        finally:
            # set readiness to True because all is done
            self.ready = True

        if successfully:
            logging.info("transcoder: Successfully transcoded: " + str(cachePath))
            self.exit_code = 0
