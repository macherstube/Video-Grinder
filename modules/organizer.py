#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##########################################################
# title:  organizer.py
# author: Josias Bruderer
# date:   13.08.2021
# desc:   organize transcoded and current media
##########################################################

import time as teatime
from datetime import datetime, time
import os
from pathlib import Path
from plexapi.server import PlexServer
import threading
import glob
import shutil


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


class Organizer:

    def __init__(self, config):
        self.ready = False
        self.config = config
        self.createTranscoderCache()
        self.plexSrv = PlexServer(self.config["Plex-Server"], self.config["X-Plex-Token"])
        self.organizedFiles = []
        self.plexStatus = 1
        self.ready = True

    def set_organized_file(self, file):
        self.organizedFiles.append(file)

    def createTranscoderCache(self):
        Path(self.config["transcoderCache"]).mkdir(parents=True, exist_ok=True)

    def stopPlex(self):
        if self.plexStatus == 1:
            if self.config["MODE"] == "development" or self.config["MODE"] == "debug":
                print("Run Stop Command for PlexService")
            os.system(self.config["plexServiceStopCommand"])
            self.plexStatus = 0

    def startPlex(self):
        if self.plexStatus == 0:
            if self.config["MODE"] == "development" or self.config["MODE"] == "debug":
                print("Run Start Command for PlexService")
            teatime.sleep(5)
            os.system(self.config["plexServiceStartCommand"])
            teatime.sleep(5)
            self.plexStatus = 1

    def transcodedFiles(self):
        files = []
        for file in glob.iglob(self.config["transcoderCache"] + "/**/*." + self.config["targetContainer"],
                               recursive=True):
            files.append(file)
        return files

    def updatePlexLibaray(self):
        for s in self.config["plexLibrarySections"]:
            lib = self.plexSrv.library.section(s)
            lib.update()

    def analyzePlexLibrary(self):
        for s in self.config["plexLibrarySections"]:
            lib = self.plexSrv.library.section(s)
            lib.analyze()

    def ready_to_analyze(self):
        start = self.config["plexAnalyzeTimeWindow"]["start"]
        end = self.config["plexAnalyzeTimeWindow"]["end"]
        return is_time_between(time(start[0], start[1]), time(end[0], end[1]))

    @threaded
    def organize(self, files):
        self.ready = False
        changedfile = False

        if self.config["MODE"] == "development" or self.config["MODE"] == "debug":
            print("Start organizing files.")

        for tf in self.transcodedFiles():
            for f in files:
                if str(f.ratingKey) == Path(tf).parent.name:
                    if self.config["MODE"] == "development" or self.config["MODE"] == "debug":
                        if self.config["MODE"] == "development" or self.config["MODE"] == "debug":
                            print("Move ", tf, "to", Path(f.locations[0]).parent.joinpath(Path(tf).name))
                        if self.config["readonly"] == "False":
                            self.stopPlex()
                            changedfile = True
                            shutil.move(tf, Path(f.locations[0]).parent.joinpath(Path(tf).name))
                        if Path(f.locations[0]).name != Path(tf).name:
                            if self.config["MODE"] == "development" or self.config["MODE"] == "debug":
                                print("Delete old file: ", Path(f.locations[0]))
                            if self.config["readonly"] == "False":
                                self.stopPlex()
                                changedfile = True
                                os.remove(f.locations[0])
                    self.set_organized_file(f)
            if self.config["readonly"] == "False":
                if self.config["MODE"] == "development" or self.config["MODE"] == "debug":
                    print("Delete orphan files and folder: ", tf)
                shutil.rmtree(Path(tf).parent)
        self.startPlex()
        if changedfile:
            self.updatePlexLibaray()
            if self.ready_to_analyze():
                self.analyzePlexLibrary()
        if self.config["MODE"] == "development" or self.config["MODE"] == "debug":
            print("End organizing files.")
        self.ready = True
