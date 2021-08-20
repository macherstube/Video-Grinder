#!/usr/bin/env python3
# -*- coding: utf-8 -*-

###################################################################
# title:  Video-Grinder
# author: Josias Bruderer
# date:   17.08.2021
# desc:   Grinds Videos to different format  in a Plex Environment
###################################################################

import sys
from pathlib import Path
import logging


try:
    # prepare to load project specific libraries, therefore we add project_path to sys.path
    project_path = Path.cwd().parent
    if project_path not in sys.path:
        sys.path.append(str(project_path))

    # import modules
    from modules import config_loader
    from modules import sentry
    from modules import controller
    from modules import csv_logger

    # load config: use config path from console parameter or default path
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = r"config/default.json"

    # load sentry for crash analytics
    sentryEnabled = False
    sentryconfig = Path(config_file).parent.joinpath("sentry.txt")
    if sentryconfig.is_file() and len(sentryconfig.read_text()) > 0:
        sentry.sentry_init(sentryconfig.read_text())
        sentryEnabled = True

    # create config object using the provided config file
    cfg = config_loader.Cfg(config_file)

    # setup logging to file and console
    logging.basicConfig(filename=cfg.config["logFile"],
                        level=eval("logging." + cfg.config["logLevel"]),
                        format='%(asctime)s; %(levelname)s; %(message)s')
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

    # create global CSV Logger
    csv_logger.__CSV__ = csv_logger.csvLogger(cfg.config["csvLogFile"],
                                              ["date", "type", "action", "code", "status", "Old", "New", "aspectRatio",
                                               "audioChannels", "audioCodec", "audioProfile", "bitrate", "container",
                                               "duration", "has64bitOffsets", "height", "id", "isOptimizedVersion",
                                               "key", "optimizedForStreaming", "proxyType", "target", "title",
                                               "videoCodec", "videoFrameRate", "videoProfile",
                                               "videoResolution", "width"])

    # create new instance of controller
    ctrl = controller.Ctrl(cfg.config)

    # tell the controller to start its work
    ctrl.take_control()

except Exception as e:
    # if an exception occurs log message and send exception to sentry crash analytics
    logging.error("Unexpected error:", exc_info=True, stack_info=True)
    if sentryEnabled:
        sentry.capture_exception(e)
