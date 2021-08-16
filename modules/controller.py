#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##########################################################
# title:  controller.py
# author: Josias Bruderer
# date:   13.08.2021
# desc:   controlls the whole operation :)
##########################################################

import time
import warnings

from modules import monitor
from modules import transcoder
from modules import organizer
from enum import Enum, auto


class CtrlStates(Enum):
    IDLE = auto()
    SELFCHECK = auto()
    QUEUE = auto()
    ORGANIZE = auto()


class Ctrl:
    def __init__(self, config):
        self.config = config
        self.monitors = []
        self.transcoders = []
        self.organizers = []
        self.runningSpeed = self.config["runningSpeed"]
        self.addingInProgress = {"monitors": False, "transcoders": False, "organizers": False}
        self.__state = CtrlStates.IDLE

    def add_monitor(self):
        self.addingInProgress["monitors"] = True
        self.monitors.append(monitor.Monitor(self.config))
        self.addingInProgress["monitors"] = False
        if self.config["MODE"] == "development" or self.config["MODE"] == "debug":
            print("monitor created")

    def get_monitor(self):
        for mo in self.monitors:
            if mo.ready:
                return mo
        return False

    def add_transcoder(self):
        self.addingInProgress["transcoders"] = True
        self.transcoders.append(transcoder.Transcoder(self.config))
        self.addingInProgress["transcoders"] = False
        if self.config["MODE"] == "development" or self.config["MODE"] == "debug":
            print("transcoder created")

    def get_transcoder(self):
        for tr in self.transcoders:
            if tr.ready:
                return tr
        return False

    def get_busy_transcoders(self):
        tra = []
        for tr in self.transcoders:
            if not tr.ready:
                tra.append(tr)
        return tra

    def add_organizer(self):
        self.addingInProgress["organizers"] = True
        self.organizers.append(organizer.Organizer(self.config))
        self.addingInProgress["organizers"] = False
        if self.config["MODE"] == "development" or self.config["MODE"] == "debug":
            print("organizer created")

    def get_organizer(self):
        for org in self.organizers:
            if org.ready:
                return org
        return False

    def get_busy_organizers(self):
        orga = []
        for org in self.organizers:
            if not org.ready:
                orga.append(org)
        return orga

    def take_control(self):
        while True:
            # delay loop to avoid heavy load
            time.sleep(self.runningSpeed)
            if self.config["MODE"] == "development":
                print("State: " + str(self.__state))

            # Here the state machine happens
            if self.__state == CtrlStates.IDLE:
                """STATE: IDLE"""
                if self.get_monitor():
                    self.get_monitor().update_data()
                self.__state = CtrlStates.SELFCHECK
                continue

            if self.__state == CtrlStates.SELFCHECK:
                """STATE: SELFCHECK"""
                # check if at least one monitor exists (you should use only 1 monitor)
                if len(self.monitors) == 0 and not self.addingInProgress["monitors"]:
                    self.add_monitor()

                # check if at least one transcoder exists (you can have multiple transcoders)
                if len(self.transcoders) < self.config["transcoderCount"] and not self.addingInProgress["transcoders"]:
                    self.add_transcoder()

                # check if at least one organizer exists (you should use only 1 monitor)
                if len(self.organizers) == 0 and not self.addingInProgress["organizers"]:
                    self.add_organizer()
                self.__state = CtrlStates.QUEUE
                continue

            if self.__state == CtrlStates.QUEUE:
                """STATE: QUEUE"""
                # get an available monitor and check if it is ready for transcode
                mo = self.get_monitor()
                if mo:
                    for tr in self.transcoders:
                        if tr.exit_code not in [-1, 0, 404, 999] and tr.file is not None:
                            mo.remove_current_transcoding(tr.file)
                            tr.exit_code = 999
                        elif tr.exit_code == 0 and tr.file is not None:
                            mo.remove_current_transcoding(tr.file)
                            mo.set_successfully_transcoded(tr.file)
                            tr.exit_code = 999
                        elif tr.exit_code == 404 and tr.file is not None:
                            mo.remove_current_transcoding(tr.file)
                            mo.set_failed_to_transcode(tr.file)
                            tr.exit_code = 999
                    if len(self.get_busy_organizers()) == 0:
                        if self.config["MODE"] == "development":
                            print(mo.get_states())
                            print(mo.get_files())

                        if len(mo.get_files()) > 0 and mo.ready_to_transcode():
                            # get an available transcoder and send task for transcoding
                            tr = self.get_transcoder()
                            if tr:
                                file = mo.get_files()[0]
                                mo.set_current_transcoding(file)
                                tr.transcode(file)
                        else:
                            if self.config["MODE"] == "development" or self.config["MODE"] == "debug":
                                if not mo.ready_to_transcode():
                                    print("Transcoder not ready: ", str(mo.failureReason))
                                if len(mo.get_files()) == 0:
                                    print("No files to transcode.")
                                    self.__state = CtrlStates.ORGANIZE
                                    continue
                        if mo.queue_full():
                            self.__state = CtrlStates.ORGANIZE
                            continue
                self.__state = CtrlStates.IDLE
                continue

            if self.__state == CtrlStates.ORGANIZE:
                """STATE: ORGANIZE"""
                # get an available organizer and start organizing
                org = self.get_organizer()
                mo = self.get_monitor()
                if org and mo:
                    #do only organize when nothing is being transcoded...
                    if len(self.get_busy_transcoders()) == 0:
                        if mo.ready_to_organize():
                            org.organize(mo.successfullyTranscoded)
                        else:
                            if self.config["MODE"] == "development" or self.config["MODE"] == "debug":
                                warnings.warn("Organizer not ready: " + str(mo.failureReason))
                self.__state = CtrlStates.IDLE
                continue
