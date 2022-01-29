#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##########################################################
# title:  controller.py
# author: Josias Bruderer
# date:   29.01.2022
# desc:   controls the whole operation :)
##########################################################

import logging
import time
from modules import monitor
from modules import transcoder
from modules import organizer
from modules import mailer
from enum import Enum, auto


class CtrlStates(Enum):
    IDLE = auto()
    SELFCHECK = auto()
    QUEUE = auto()
    ORGANIZE = auto()


class Ctrl:
    def __init__(self, config):
        logging.info("controller: initializing")
        self.config = config
        self.monitors = []
        self.transcoders = []
        self.organizers = []
        self.runningSpeed = self.config["runningSpeed"]
        self.addingInProgress = {"monitors": False, "transcoders": False, "organizers": False}
        self.__state = CtrlStates.IDLE
        logging.info("controller: initialized")

    def add_monitor(self):
        self.addingInProgress["monitors"] = True
        self.monitors.append(monitor.Monitor(self, self.config))
        self.addingInProgress["monitors"] = False
        logging.info("monitor: created")

    def get_monitor(self):
        self.monitors = [mo for mo in self.monitors if mo.zombie is False]
        for mo in self.monitors:
            if mo.ready:
                return mo
        return False

    def get_monitors(self):
        mos = []
        self.monitors = [mo for mo in self.monitors if mo.zombie is False]
        for mo in self.monitors:
            if mo.ready:
                mos.append(mo)
        return mos

    def get_sleeping_monitors(self):
        mos = []
        self.monitors = [mo for mo in self.monitors if mo.zombie is False]
        for mo in self.monitors:
            if mo.sleeping:
                mos.append(mo)
        return mos

    def add_transcoder(self):
        self.addingInProgress["transcoders"] = True
        self.transcoders.append(transcoder.Transcoder(self.config))
        self.addingInProgress["transcoders"] = False
        logging.info("transcoder: created")

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
        logging.info("organizer: created")

    def get_organizer(self):
        self.organizers = [org for org in self.organizers if org.zombie is False]
        for org in self.organizers:
            if org.ready:
                return org
        return False

    def get_busy_organizers(self):
        orga = []
        self.organizers = [org for org in self.organizers if org.zombie is False]
        for org in self.organizers:
            if not org.ready:
                orga.append(org)
        return orga

    def take_control(self):
        while True:
            # delay loop to avoid heavy load
            time.sleep(self.runningSpeed)
            logging.debug("state machine: " + str(self.__state))

            # Here the state machine happens
            if self.__state == CtrlStates.IDLE:
                """STATE: IDLE - run maintenance-like jobs"""
                # check if a organizer is currently organizing files.
                # If so, send the monitors to sleep; if not, wake the sleeping monitors up.
                # Why? - Because no transcode and no plex request should be made during organizing.
                organizing = False
                for org in self.get_busy_organizers():
                    if org.organizing:
                        organizing = True
                if organizing:
                    # set monitors to sleep
                    for mo in self.get_monitors():
                        mo.sleep()
                else:
                    # wake up monitors
                    for mo in self.get_sleeping_monitors():
                        mo.wakeup()

                # get an available monitor and initiate a data update.
                if self.get_monitor():
                    self.get_monitor().update_data()

                # Next step: run selfchecks
                self.__state = CtrlStates.SELFCHECK
                continue

            if self.__state == CtrlStates.SELFCHECK:
                """STATE: SELFCHECK - check if there are enough monitors, transcoders and organizers or create them"""
                # make sure that one monitor exists (you should use only 1 monitor)
                if len(self.monitors) == 0 and not self.addingInProgress["monitors"]:
                    self.add_monitor()

                # check if enough transcoders exist (you can define the number of transcoders in config)
                if len(self.transcoders) < self.config["transcoderCount"] and not self.addingInProgress["transcoders"]:
                    self.add_transcoder()

                # make sure that one organizer exists (you should use only 1 monitor)
                if len(self.organizers) == 0 and not self.addingInProgress["organizers"]:
                    self.add_organizer()

                # Next step: work of the queue
                self.__state = CtrlStates.QUEUE
                continue

            if self.__state == CtrlStates.QUEUE:
                """STATE: QUEUE - run a transcode job if everything is right"""
                # get an available monitor and check if it is ready for transcode
                mo = self.get_monitor()
                if mo:
                    # do stuff with finished transcoders
                    for tr in self.transcoders:
                        # something unexpected happened while transcoding
                        # -> remove_x will keep the file for transcoding in queue and causes another transcoding
                        if tr.exit_code not in [-1, 0, 1, 404, 405, 500, 999] and tr.file is not None:
                            mo.remove_current_transcoding(tr.file)
                            tr.exit_code = 999
                        # last transcoding was successfully
                        # -> remove_x and set_x will remove the file from transcoder queue and add it to organizer queue
                        elif tr.exit_code in [0, 1] and tr.file is not None:
                            mo.remove_current_transcoding(tr.file)
                            mo.set_successfully_transcoded(tr.file)
                            tr.exit_code = 999
                        # last transcoding was not successfully
                        # -> remove_x and set_x will remove the file from transcoder queue
                        elif tr.exit_code in [404, 405, 500] and tr.file is not None:
                            mo.remove_current_transcoding(tr.file)
                            mo.set_failed_to_transcode(tr.file)
                            tr.exit_code = 999

                    # do only proceed if no organizer is busy
                    if len(self.get_busy_organizers()) == 0:
                        file = mo.get_file()

                        logging.debug("monitor: states before transcoding: " + str(mo.get_states()))
                        # logging.debug("monitor: file before transcoding: " + str(file))

                        # do only proceed if files are in queue and one transcoder is ready
                        if file and mo.ready_to_transcode():
                            # get an available transcoder and send task for transcoding
                            tr = self.get_transcoder()
                            if tr:
                                # mark file as being currently transcoded to avoid duplicated jobs
                                mo.set_current_transcoding(file)
                                # send transccode job ("Energize" is the keyword)
                                tr.transcode(file)
                        else:
                            if not mo.ready_to_transcode():
                                if self.get_transcoder():
                                    logging.info("monitor: not ready to transcode: " + str(mo.failureReason))
                            if not file:
                                logging.info("monitor: no files to transcode.")
                                # since there are no files left to transcode we go right to organizing state
                                self.__state = CtrlStates.ORGANIZE
                                continue
                        # if the transcoder queue is full go to organizing state
                        if mo.queue_full():
                            # Next step: organize the transcoded files
                            self.__state = CtrlStates.ORGANIZE
                            continue
                # Next step: go to idle state, read: begin from start
                self.__state = CtrlStates.IDLE
                continue

            if self.__state == CtrlStates.ORGANIZE:
                """STATE: ORGANIZE - do stuff with the transcoded files (order them to plex library)"""
                # get an available organizer and monitor
                org = self.get_organizer()
                mo = self.get_monitor()
                if org and mo:
                    # do only organize when nothing is being transcoded
                    if len(self.get_busy_transcoders()) == 0:
                        # if monitor indicated readiness for organizing, start organizing
                        if mo.ready_to_organize():
                            mailer.__MAIL__.send("Video-Grinder: Organizer starts",
                                                 "We just let you know that organizer is starting. Following files are queued:\n\n" +
                                                 str(mo.get_successfully_transcoded()))
                            org.organize(mo.get_successfully_transcoded())
                            mailer.__MAIL__.send("Video-Grinder: Organizer ends",
                                                 "We just let you know that organizer has ended.")
                        else:
                            logging.info("organizer: not ready: " + str(mo.failureReason))
                # Next step: go to idle state, read: begin from start
                self.__state = CtrlStates.IDLE
                continue
