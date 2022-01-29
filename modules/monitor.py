#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##########################################################
# title:  monitor.py
# author: Josias Bruderer
# date:   27.01.2022
# desc:   monitors the whole operation :)
##########################################################

import logging
from datetime import datetime, time
import psutil
import plexapi
from plexapi.server import PlexServer
import math
from pathlib import Path
import shutil
import GPUtil
import threading


def threaded(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()

    return wrapper


def is_time_between(begin_time, end_time, check_time=None):
    # If check time is not given, default to current UTC time
    check_time = check_time or datetime.utcnow().time()
    if begin_time < end_time:
        return check_time >= begin_time and check_time <= end_time
    else:  # crosses midnight
        return check_time >= begin_time or check_time <= end_time


def wMean(vs, r=0):
    """get a weighted mean of an array: values with higher index as well as higher values counts more (exponential)"""
    s = 0
    if len(vs) > 0:
        for i, v in enumerate(vs):
            if not v:
                v = 0
            s = s + (int(v) ** 2) * (i + 1)
    else:
        return 0
    return round(math.sqrt(s / int(len(vs) * (len(vs) + 1) / 2)), r)


class Monitor:

    def __init__(self, parent, config):
        self.ctrl = parent
        self.config = config
        self.states = {"sys": {}, "plex": {}, "fs": {}, "gpu": {}, "veto": {}}
        self.plexLibrary = {"date": 0, "files": []}
        self.plexStats = {"date": 0}
        self.history = {"current":[], "success":[], "failure":[], "all":[]}
        self.successfullyTranscoded = []
        self.failureReason = {}
        self.ready = False
        self.zombie = False
        self.sleeping = False
        self.plexSrv = None
        if self.setup_plexapi():
            self.update_data()

    def setup_plexapi(self):
        try:
            self.plexSrv = PlexServer(self.config["plexServer"], self.config["X-Plex-Token"])
            return True
        except Exception as e:
            logging.critical("monitor: connecting to plex not possible: " + str(e))
            self.zombie = True
            return False

    def destroy_plexapi(self):
        self.plexSrv = None

    def sleep(self):
        self.ready = False
        self.sleeping = True
        self.destroy_plexapi()

    def wakeup(self):
        self.setup_plexapi()
        self.sleeping = False
        self.ready = True

    @threaded
    def update_data(self):
        # set readiness to False to avoid conflicts
        self.ready = False
        try:
            self.sys()
            self.plex()
            self.fs()
            self.gpu()
            self.plexlibrary()
            self.veto()
            # set readiness to True because all is done
            self.ready = True
        except Exception as e:
            logging.critical("monitor: error while updating: " + str(e))
            self.zombie = True
            return False

    def get_veto_organize(self):
        return self.states["veto"]["organizer"]

    def set_failed_to_transcode(self, file):
        self.history["failure"].append(file.ratingKey)

    def set_successfully_transcoded(self, file):
        self.history["success"].append(file.ratingKey)
        self.successfullyTranscoded.append(file)

    def get_successfully_transcoded(self):
        return self.successfullyTranscoded

    def set_current_transcoding(self, file):
        self.history["current"].append(file.ratingKey)

    def remove_current_transcoding(self, file):
        try:
            self.history["current"].remove(file.ratingKey)
        except ValueError as e:
            logging.warning("monitor: tried to remove file from current transcoding but this failed: "
                            + str(file).encode('ascii', 'replace').decode())
            pass

    def queue_full(self):
        return not eval('self.states["fs"]["transcoderCacheSize"]' +
                    self.config["transcoderReady"]["fs"]["transcoderCacheSize"]) \
               or not eval('self.states["fs"]["transcoderCacheDiskFree"]' +
                        self.config["transcoderReady"]["fs"]["transcoderCacheDiskFree"])

    def ready_to_transcode(self):
        # loop through the config and crosscheck with current state
        for counter in self.config["transcoderReady"]:
            for value in self.config["transcoderReady"][counter]:
                if self.config["transcoderReady"][counter][value] != -1:
                    if not eval("self.states[counter][value]" + self.config["transcoderReady"][counter][value]):
                        self.failureReason = {
                            "counter": counter,
                            "value": value,
                            "must": self.config["transcoderReady"][counter][value],
                            "is": self.states[counter][value]
                        }
                        return False
        self.failureReason = {}
        return True

    def ready_to_organize(self):
        # loop through the config and crosscheck with current state
        for counter in self.config["organizerReady"]:
            for value in self.config["organizerReady"][counter]:
                if value == "datetime" and len(self.config["organizerReady"][counter][value]) >= 1:
                    istime = False
                    for v in self.config["organizerReady"][counter][value]:
                        start = v["start"]
                        end = v["end"]
                        if is_time_between(time(start[0], start[1]), time(end[0], end[1]),
                                           self.states[counter][value]):
                            istime = True
                    if not istime:
                        self.failureReason = {
                            "counter": counter,
                            "value": value,
                            "must": self.config["organizerReady"][counter][value],
                            "is": self.states[counter][value]
                        }
                        return False
                elif self.config["organizerReady"][counter][value] != -1:
                    if not eval("self.states[counter][value]" + self.config["organizerReady"][counter][value]):
                        self.failureReason = {
                            "counter": counter,
                            "value": value,
                            "must": self.config["organizerReady"][counter][value],
                            "is": self.states[counter][value]
                        }
                        return False
        self.failureReason = {}
        return True

    def get_states(self):
        return self.states

    def get_file(self):
        self.history["all"] = self.history["current"] + self.history["success"] + self.history["failure"]
        for file in self.plexLibrary["files"]:
            # check if file is neither currently transcoding nor already processed
            if len(self.history["all"]) == 0 or file.ratingKey not in self.history["all"]:
                # check if a filter is configured
                if len(self.config["plexLibraryFilesFilter"]) != 0:
                    ok = True
                    # loop through all filters and check if they apply to the file
                    for f in self.config["plexLibraryFilesFilter"]:
                        if not hasattr(file, 'media') \
                                or not len(file.media) > 0 \
                                or not eval("file.media[0]." + f + " " + self.config["plexLibraryFilesFilter"][f]):
                            ok = False
                    if ok:
                        return file
                else:
                    return file
        return False

    def sys(self):
        # ready system parameters
        self.states["sys"]["cpu"] = psutil.cpu_percent()
        self.states["sys"]["memory"] = psutil.virtual_memory().percent
        self.states["sys"]["datetime"] = datetime.now().time()

    def plex(self):
        # read plex parameters: do only update these values after specific delay (defined in config)
        now = datetime.timestamp(datetime.now())
        if now > self.plexStats["date"] + self.config["plexStatsUpdateInterval"]:
            resources = self.plexSrv.resources()
            self.states["plex"]["PlayingSessions"] = self.plexSrv.sessions()
            self.states["plex"]["PlayingSessionsCount"] = len(self.plexSrv.sessions())
            self.states["plex"]["TranscodeSessions"] = self.plexSrv.transcodeSessions()
            self.states["plex"]["TranscodeSessionsCount"] = len(self.plexSrv.transcodeSessions())
            self.states["plex"]["hostCpuUtilization"] = wMean([r.hostCpuUtilization for r in resources])
            self.states["plex"]["hostMemoryUtilization"] = wMean([r.hostMemoryUtilization for r in resources])
            self.states["plex"]["processCpuUtilization"] = wMean([r.processCpuUtilization for r in resources])
            self.states["plex"]["processMemoryUtilization"] = wMean([r.processMemoryUtilization for r in resources])
            self.states["plex"]["TranscodeSessionsDelta"] = self.config["transcoderCount"] - \
                                                            len(self.ctrl.get_busy_transcoders()) - \
                                                            len(self.plexSrv.transcodeSessions())
            self.plexStats["date"] = now

    def fs(self):
        # read filesystem parameters
        try:
            self.states["fs"]["transcoderCacheSize"] = sum(
                f.stat().st_size for f in Path(self.config["transcoderCache"]).glob('**/*') if f.is_file())
        except FileNotFoundError:
            self.states["fs"]["transcoderCacheSize"] = 0
        self.states["fs"]["transcoderCacheDiskTotal"], \
        self.states["fs"]["transcoderCacheDiskUsed"], \
        self.states["fs"]["transcoderCacheDiskFree"], = shutil.disk_usage(self.config["transcoderCache"])

    def gpu(self):
        # read gpu parameters if any gpu is found
        gpus = GPUtil.getGPUs()
        if len(gpus) > 0:
            gpu = gpus[0]
            self.states["gpu"]["load"] = gpu.load * 100
            self.states["gpu"]["memoryUtil"] = gpu.memoryUtil * 100
            self.states["gpu"]["temperature"] = gpu.temperature
        else:
            self.states["gpu"]["load"] = 0
            self.states["gpu"]["memoryUtil"] = 0
            self.states["gpu"]["temperature"] = 0

    def veto(self):
        if Path(self.config["organizerVetoFile"]).is_file():
            with open(self.config["organizerVetoFile"], 'r') as f:
                veto = f.read()
                if veto == "true":
                    self.states["veto"]["organizer"] = True
                elif veto == "false":
                    self.states["veto"]["organizer"] = False
                else:
                    self.states["veto"]["organizer"] = -1
        else:
            self.states["veto"]["organizer"] = -1

    def plexlibrary(self):
        # update local copy of plexlibrary after specific delay (defined in config)
        now = datetime.timestamp(datetime.now())
        if now > self.plexLibrary["date"] + self.config["plexLibraryUpdateInterval"]:
            logging.info("monitor: library update started")
            self.plexLibrary["files"] = []
            # get files of everry section
            for s in self.config["plexLibrarySections"]:
                lib = self.plexSrv.library.section(s)
                if isinstance(lib, plexapi.library.MovieSection):
                    if len(self.config["plexLibraryQueryFilter"]) != 0:
                        self.plexLibrary["files"] = self.plexLibrary["files"] \
                                                    + lib.searchMovies(sort=self.config["plexLibrarySort"]["movies"],
                                                                       **self.config["plexLibraryQueryFilter"])
                    else:
                        self.plexLibrary["files"] = self.plexLibrary["files"] + lib.searchMovies(sort=self.config["plexLibrarySort"]["movies"])
                elif isinstance(lib, plexapi.library.ShowSection):
                    if len(self.config["plexLibraryQueryFilter"]) != 0:
                        self.plexLibrary["files"] = self.plexLibrary["files"] \
                                                    + lib.searchEpisodes(sort=self.config["plexLibrarySort"]["shows"],
                                                                         **self.config["plexLibraryQueryFilter"])
                    else:
                        self.plexLibrary["files"] = self.plexLibrary["files"] + lib.searchEpisodes(sort=self.config["plexLibrarySort"]["shows"])
                elif isinstance(lib, plexapi.library.MusicSection):
                    # ignore music
                    pass
                elif isinstance(lib, plexapi.library.PhotoSection):
                    # ignore photos
                    pass

            self.plexLibrary["date"] = now
            # reset failed transcoded files: plex data is quite up to date and therefore stuff could have changed
            self.history["failure"] = []
            logging.info("monitor: library update ended")