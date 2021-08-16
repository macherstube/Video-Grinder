#!/usr/bin/env python3
# -*- coding: utf-8 -*-

################################################################
# title:  Video-Grinder
# author: Josias Bruderer
# date:   13.08.2021
# desc:   Grinds Videos to h265 in a Plex Environment
################################################################

import sys
from pathlib import Path
import traceback


try:
    project_path = Path.cwd().parent

    # prepare to load project specific libraries
    if project_path not in sys.path:
        sys.path.append(str(project_path))

    # import modules
    from modules import config_loader
    from modules import sentry
    from modules import controller

    # load config
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = r"config/default.json"

    # load sentry for crash analytics
    sentryconfig = Path(config_file).parent.joinpath("sentry.txt")
    if sentryconfig.is_file() and len(sentryconfig.read_text()) > 0:
        sentry.sentry_init(sentryconfig.read_text())

    cfg = config_loader.Cfg(config_file)

    # here we gonna call the controller
    ctrl = controller.Ctrl(cfg.config)
    ctrl.take_control()

except Exception as e:
    print(traceback.format_exc())
    sentry.capture_exception(e)
