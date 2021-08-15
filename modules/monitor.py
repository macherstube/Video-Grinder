#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##########################################################
# title:  monitor.py
# author: Josias Bruderer
# date:   13.08.2021
# desc:   monitors the whole operation :)
##########################################################

from datetime import datetime
import psutil
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


def wMean(vs, r=0):
    """get a weighted mean of an array: values with higher index as well as higher values counts more (exponential)"""
    s = 0
    for i, v in enumerate(vs):
        s = s + (int(v) ** 2) * (i + 1)
    return round(math.sqrt(s / int(len(vs) * (len(vs) + 1) / 2)), r)


class Monitor:

    def __init__(self, config):
        self.config = config
        self.states = {"sys": {}, "plex": {}, "fs": {}, "gpu": {}}
        self.plexLibrary = {"date": 0, "files": []}
        self.currentTranscoding = []
        self.ready = False
        self.plexSrv = PlexServer(self.config["Plex-Server"], self.config["X-Plex-Token"])
        self.failureReason = {}
        self.update_data()

    @threaded
    def update_data(self):
        self.ready = False
        self.sys()
        self.plexsessions()
        self.fs()
        self.gpu()
        self.plexlibrary()
        self.ready = True

    def set_current_transcoding(self, file):
        self.currentTranscoding.append(file)

    def remove_current_transcoding(self, file):
        self.currentTranscoding.remove(file)

    def queue_full(self):
        return eval('self.states["fs"]["transcoderCacheSize"]' +
                    self.config["transcoderReady"]["fs"]["transcoderCacheSize"]) \
               or eval('self.states["fs"]["transcoderCacheDiskFree"]' +
                        self.config["transcoderReady"]["fs"]["transcoderCacheDiskFree"])

    def ready_to_transcode(self):
        for counter in self.config["transcoderReady"]:
            for value in self.config["transcoderReady"][counter]:
                if self.config["transcoderReady"][counter][value] != -1:
                    if not eval("self.states[counter][value]" + self.config["transcoderReady"][counter][value]):
                        self.failureReason = {
                            "counter": counter,
                            "value": value,
                            "must": self.config["transcoderReady"][counter][value],
                            "have": self.states[counter][value]
                        }
                        return False
        self.failureReason = {}
        return True

    def get_states(self):
        return self.states

    def get_files(self):
        return [x for x in self.plexLibrary["files"] if x not in self.currentTranscoding]

    def sys(self):
        # gives a single float value
        self.states["sys"]["cpu"] = psutil.cpu_percent()

        # gives an object with many fields
        self.states["sys"]["memory"] = psutil.virtual_memory().percent

    def plexsessions(self):
        resources = self.plexSrv.resources()
        self.states["plex"]["PlayingSessions"] = self.plexSrv.sessions()
        self.states["plex"]["PlayingSessionsCount"] = len(self.plexSrv.sessions())
        self.states["plex"]["TranscodeSessions"] = self.plexSrv.transcodeSessions()
        self.states["plex"]["TranscodeSessionsCount"] = len(self.plexSrv.transcodeSessions())
        self.states["plex"]["hostCpuUtilization"] = wMean([r.hostCpuUtilization for r in resources])
        self.states["plex"]["hostMemoryUtilization"] = wMean([r.hostMemoryUtilization for r in resources])
        self.states["plex"]["processCpuUtilization"] = wMean([r.processCpuUtilization for r in resources])
        self.states["plex"]["processMemoryUtilization"] = wMean([r.processMemoryUtilization for r in resources])

    def fs(self):
        self.states["fs"]["transcoderCacheSize"] = sum(
            f.stat().st_size for f in Path(self.config["transcoderCache"]).glob('**/*') if f.is_file())
        self.states["fs"]["transcoderCacheDiskTotal"], \
        self.states["fs"]["transcoderCacheDiskUsed"], \
        self.states["fs"]["transcoderCacheDiskFree"], = shutil.disk_usage(self.config["transcoderCache"])

    def gpu(self):
        gpu = GPUtil.getGPUs()[0]
        self.states["gpu"]["load"] = gpu.load * 100
        self.states["gpu"]["memoryUtil"] = gpu.memoryUtil * 100
        self.states["gpu"]["temperature"] = gpu.temperature

    def plexlibrary(self):
        now = datetime.timestamp(datetime.now())
        if now > self.plexLibrary["date"] + self.config["plexLibraryUpdateInterval"]:
            print("update library")
            self.plexLibrary["files"] = []
            for s in self.config["plexLibrarySections"]:
                lib = self.plexSrv.library.section(s)
                self.plexLibrary["files"] = self.plexLibrary["files"] + lib.all()

            self.plexLibrary["date"] = now
