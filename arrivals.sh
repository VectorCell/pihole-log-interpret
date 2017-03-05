#!/bin/bash

tail -F /var/log/pihole.log | ./arrivals.py
