#!/usr/bin/env python3
# -*- coding: utf-8 -*-

###################################################################
# title:  csv_logger
# author: Josias Bruderer
# date:   20.08.2021
# desc:   write logs to csv
###################################################################

import csv
from datetime import datetime

__CSV__ = None

class csvLogger:

    def __init__(self, path, header):
        self.path = path
        self.header = header

        f = open(self.path, 'w', encoding='UTF8', newline='', buffering=1)
        self.writer = csv.writer(f)
        self.writer.writerow(self.header)

    def log(self, row):
        self.writer.writerow([str(datetime.now())] + row)
