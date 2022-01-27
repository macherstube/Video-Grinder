#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##########################################################
# title:  organizer.py
# author: Josias Bruderer
# date:   27.01.2022
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

from modules import csv_logger


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
        self.zombie = False
        self.config = config
        self.createTranscoderCache()
        self.plexSrv = None
        self.dbconn = None
        self.organizedFiles = []
        self.deleteQueue = []
        self.moveQueue = []
        if self.setup_plexapi():
            self.plexStatus = 1
            # set readiness to True because all is done
            self.ready = True
        self.organizing = False


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

    def set_organized_file(self, file):
        self.organizedFiles.append(file)

    def createTranscoderCache(self):
        Path(self.config["transcoderCache"]).mkdir(parents=True, exist_ok=True)
        for f in os.listdir(Path(self.config["transcoderCache"])):
            shutil.rmtree(os.path.join(Path(self.config["transcoderCache"]), f))

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
                    path = Path(f.locations[0])
                    if "fakeFileSystem" in self.config and len(self.config["fakeFileSystem"]) > 0:
                        path = Path(str(path).replace(self.config["fakeFileSystem"]["search"][0],
                                                      self.config["fakeFileSystem"]["replace"][0])
                                    .replace(self.config["fakeFileSystem"]["search"][1],
                                             self.config["fakeFileSystem"]["replace"][1]))
                    logging.info("organizer: queue move " + str(tf).encode('ascii', 'replace').decode() + " to "
                                 + str(path.parent.joinpath(Path(tf).name)).encode('ascii', 'replace').decode())
                    # do only move files if not readonly mode
                    if self.config["readonly"] == "False":
                        self.stopPlex()             # make sure plex service is not running
                        changedfile = True          # this will cause a db update (commit)
                        self.moveQueue.append({"from": tf,"to": path.parent.joinpath(Path(tf).name)})
                    # if the filepath has changed we need to take care of that within filesystem and plex database
                    if path.name != Path(tf).name:
                        if self.config["readonly"] == "False":
                            self.stopPlex()         # make sure plex service is not running
                            changedfile = True      # this will cause a db update (commit)

                            # update filepath in db
                            updateStr = "UPDATE media_parts SET file = \"" \
                                        + str(path.parent.joinpath(Path(tf).name)) \
                                        + "\" WHERE file = \"" + str(path) + "\" "\
                                        + "OR file = \"" + str(path).replace("\\", "/") + "\";"
                            logging.debug("organizer: queue update db: "
                                          + str(updateStr).encode('ascii', 'replace').decode())
                            dbcur.execute(updateStr)
                            if dbcur.rowcount != 1:
                                logging.warning("organizer: dbupdate could be invalid, recived " + str(dbcur.rowcount)
                                                + " and not 1 rowcount for file: " + str(f).encode('ascii', 'replace').decode() + " "
                                                + str(path.parent.joinpath(Path(tf).name)).encode('ascii', 'replace').decode())
                                csv_logger.__CSV__.log(["organizer", "db update", 1, "dbupdate could be invalid",
                                                        updateStr, str(dbcur.rowcount) + " rows changed."])
                            else:
                                csv_logger.__CSV__.log(["organizer", "db update", 0, "successfully updated",
                                                        updateStr, str(dbcur.rowcount) + " rows changed."])
                            # mark path to be deleted (that will happen after db commit)
                            self.deleteQueue.append(path)
                    self.set_organized_file(f)
        if changedfile:
            try:
                self.stopPlex()  # make sure plex service is not running

                for f in self.moveQueue:
                    logging.info("organizer: move file from: " + str(f["from"]).encode('ascii', 'replace').decode()
                                 + " to: " + str(f["to"]).encode('ascii', 'replace').decode())
                    shutil.move(f["from"], f["to"])
                    csv_logger.__CSV__.log(["organizer", "file move", 0, "successfully moved", f["from"], f["to"]])
                    # delete file and folders that were not organized: this will remove old folders and orphan files
                    logging.info(
                        "organizer: delete orphan files and folder: " + str(f["from"]).encode('ascii', 'replace').decode())
                    shutil.rmtree(Path(f["from"]).parent)

                for f in self.deleteQueue:
                    logging.info("organizer: delete old file: " + str(f).encode('ascii', 'replace').decode())
                    os.remove(f)
                    csv_logger.__CSV__.log(["organizer", "file delete", 0, "successfully deleted", f, ""])

                logging.info("organizer: commit plex db update")
                self.dbconn.commit()
                csv_logger.__CSV__.log(["organizer", "db update", 0, "successfully committed", "", ""])

            except FileNotFoundError as e:
                logging.warning("organizer: file not existing anymore: " + str(f).encode('ascii', 'replace').decode()
                                + " or " + str(f["from"]).encode('ascii', 'replace').decode())
                return
            except Exception as e:
                # If something bad happend while commiting db or filesystem we gotta shut down everything
                # and manually check the logs and do fixing stuff.
                # This is to make sure no ugly stuff happens with our library.
                logging.critical("organizer: we have a problem - like really.!: " + str(e) + " " + e.characters_written)
                os._exit(1)
                return

        self.dbconn.close()

        self.startPlex()                    # make sure plex starts again

        if changedfile:
            # update and analyze library after changes are made
            self.updatePlexLibaray()
            if self.ready_to_analyze():
                self.analyzePlexLibrary()

        self.moveQueue = []
        self.deleteQueue = []

        logging.info("organizer: end organizing files.")
        self.ready = True
