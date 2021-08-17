#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##########################################################
# title:  organizer.py
# author: Josias Bruderer
# date:   16.08.2021
# desc:   organize transcoded and current media
##########################################################

import logging
import sqlite3
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
        # set readiness to False to avoid conflicts
        self.ready = False
        self.config = config
        self.createTranscoderCache()
        self.plexSrv = None
        self.dbconn = None
        self.setup_plexapi()
        self.organizedFiles = []
        self.deleteQueue = []
        self.plexStatus = 1
        # set readiness to True because all is done
        self.ready = True
        self.organizing = False

    def setup_plexapi(self):
        self.plexSrv = PlexServer(self.config["Plex-Server"], self.config["X-Plex-Token"])

    def destroy_plexapi(self):
        self.plexSrv = None

    def set_organized_file(self, file):
        self.organizedFiles.append(file)

    def createTranscoderCache(self):
        Path(self.config["transcoderCache"]).mkdir(parents=True, exist_ok=True)

    def stopPlex(self):
        if self.plexStatus == 1:
            logging.info("organizer: run stop command for PlexService")
            # close plexapi connection
            self.destroy_plexapi()
            self.organizing = True
            # stop plex servicce
            os.system(self.config["plexServiceStopCommand"])
            teatime.sleep(5)
            self.plexStatus = 0

    def startPlex(self):
        if self.plexStatus == 0:
            logging.info("organizer: run start command for PlexService")
            # start plex servicce
            os.system(self.config["plexServiceStartCommand"])
            teatime.sleep(5)
            # start plexapi connection
            self.setup_plexapi()
            self.organizing = False
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
        self.dbconn = sqlite3.connect(self.config["plexDB"])
        dbcur = self.dbconn.cursor()

        logging.info("organizer: start organizing files")

        # loop trough files currently present in transcoder cache (filesystem)
        for tf in self.transcodedFiles():
            # loop through files currently present in transcoder successfully history (monitor)
            for f in files:
                # if file exists on filesystem and in transcoder successfully history
                if str(f.ratingKey) == Path(tf).parent.name:
                    if self.config["MODE"] == "development" or self.config["MODE"] == "debug":
                        logging.info("organizer: move " + tf + " to "
                                     + str(Path(f.locations[0]).parent.joinpath(Path(tf).name)))
                    # do only move files if not readonly mode
                    if self.config["readonly"] == "False":
                        self.stopPlex()             # make sure plex service is not running
                        changedfile = True          # this will cause a db update (commit)
                        shutil.move(tf, Path(f.locations[0]).parent.joinpath(Path(tf).name))
                    # if the filepath has changed we need to take care of that within filesystem and plex database
                    if Path(f.locations[0]).name != Path(tf).name:
                        if self.config["readonly"] == "False":
                            self.stopPlex()         # make sure plex service is not running
                            changedfile = True      # this will cause a db update (commit)

                            # update filepath in db
                            updateStr = "UPDATE media_parts SET file = \"" \
                                        + str(Path(f.locations[0]).parent.joinpath(Path(tf).name)) \
                                        + "\" WHERE media_item_id = " + str(f.ratingKey) + ";"
                            logging.debug("organizer: update db: " + updateStr)
                            dbcur.execute(updateStr)
                            if dbcur.rowcount != 1:
                                logging.warning("organizer: dbupdate could be invalid, recived " + str(dbcur.rowcount)
                                                + " and not 1 rowcount for file: " + str(f) + " "
                                                + str(Path(f.locations[0]).parent.joinpath(Path(tf).name)))

                            # mark path to be deleted (that will happen after db commit)
                            self.deleteQueue.append(f.locations[0])
                    self.set_organized_file(f)
            # delete file and folders that were not organized: this will remove old folders and orphan files
            if self.config["readonly"] == "False":
                logging.info("organizer: delete orphan files and folder: " + tf)
                shutil.rmtree(Path(tf).parent)
        if changedfile:
            try:
                logging.info("organizer: commit plex db update")
                self.dbconn.commit()
                for f in self.deleteQueue:
                    logging.info("organizer: delete old file: " + f)
                    os.remove(f)
                    self.deleteQueue.remove(f)         #WIP: check what happens when file is moved or something
            except Exception as e:
                # If something bad happend while commiting db or filesystem we gotta shut down everything
                # and manually check the logs and do fixing stuff.
                # This is to make sure no ugly stuff happens with our library.
                logging.critical("organizer: we have a problem - like really.!")
                os._exit(1)
                return
        self.dbconn.close()

        self.startPlex()                    # make sure plex starts again

        if changedfile:
            # update and analyze library after changes are made
            self.updatePlexLibaray()
            if self.ready_to_analyze():
                self.analyzePlexLibrary()
        logging.info("organizer: end organizing files.")
        self.ready = True
