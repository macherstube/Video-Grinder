#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##########################################################
# title:  controller.py
# author: Josias Bruderer
# date:   13.08.2021
# desc:   controlls the whole operation :)
##########################################################

import threading
import time
from modules import monitor
from modules import transcoder
from modules import organizer
from enum import Enum, auto


class CtrlStates(Enum):
    IDLE = auto()
    SELFCHECK = auto()
    QUEUE = auto()
    ORGANIZE = auto()


def threaded(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()
    return wrapper


class Ctrl:
    def __init__(self, config):
        self.config = config
        self.monitors = []
        self.transcoders = []
        self.organizers = []
        self.addingInProgress = {"monitors": False, "transcoders": False, "organizers": False}
        self.__state = CtrlStates.IDLE

    @threaded
    def add_monitor(self):
        self.addingInProgress["monitors"] = True
        self.monitors.append(monitor.Monitor(self.config))
        self.addingInProgress["monitors"] = False
        if self.config["MODE"] == "development":
            print("monitor created")

    def get_monitor(self):
        for mo in self.monitors:
            if mo.ready:
                return mo
        return False

    @threaded
    def add_transcoder(self):
        self.addingInProgress["transcoders"] = True
        self.transcoders.append(transcoder.Transcoder(self.config))
        self.addingInProgress["transcoders"] = False
        if self.config["MODE"] == "development":
            print("transcoder created")

    def get_transcoder(self):
        for tr in self.transcoders:
            if tr.ready:
                return tr
        return False

    @threaded
    def add_organizer(self):
        self.addingInProgress["organizers"] = True
        self.monitors.append(organizer.Organizer(self.config))
        self.addingInProgress["organizers"] = False
        if self.config["MODE"] == "development":
            print("organizer created")

    def get_organizer(self):
        for org in self.organizers:
            if org.ready:
                return org
        return False

    def take_control(self):
        while True:
            # delay loop to get a smoother load
            time.sleep(0.2)
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
                # check if at least one monitor exists
                if len(self.monitors) == 0 and not self.addingInProgress["monitors"]:
                    self.add_monitor()

                # check if at least one transcoder exists
                if len(self.transcoders) == 0 and not self.addingInProgress["transcoders"]:
                    self.add_transcoder()

                # check if at least one organizer exists
                if len(self.organizers) == 0 and not self.addingInProgress["organizers"]:
                    self.add_organizer()
                self.__state = CtrlStates.QUEUE
                continue

            if self.__state == CtrlStates.QUEUE:
                """STATE: QUEUE"""
                # get an available monitor and check if it is ready for transcode
                mo = self.get_monitor()
                if mo:
                    if(self.config["MODE"] == "development"):
                        print(mo.get_states())
                        print(mo.get_movies())

                    if(mo.ready_to_transcode()):
                        # get an available transcoder and send task for transcoding
                        tr = self.get_transcoder()
                        if tr:
                            # print object for testing
                            print(tr)
                            # TODO: send transcode job

                if 0 == 1:
                    # TODO: check if queue is full and state is ready to move files and restart plex analysis
                    self.__state = CtrlStates.ORGANIZE
                else:
                    self.__state = CtrlStates.IDLE
                continue

            if self.__state == CtrlStates.ORGANIZE:
                """STATE: ORGANIZE"""
                # get an available organizer and start organizing
                org = self.get_organizer()
                if org:
                    # print object for testing
                    print(org)
                    # TODO: start organize job

                self.__state = CtrlStates.IDLE
                continue
