#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##########################################################
# title:  sentry.py
# author: Josias Bruderer
# date:   17.08.2021
# desc:   simple implementation of sentry
##########################################################

import sentry_sdk


def sentry_init(url):
    sentry_sdk.init(
        url,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        traces_sample_rate=1.0,
        environment="development"
    )
