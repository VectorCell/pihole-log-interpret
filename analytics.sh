#!/bin/bash

tail -F /var/log/pihole.log | ./analytics.py
