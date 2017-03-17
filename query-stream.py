#!/usr/bin/env python3

import sys
import time
import datetime
import operator
import threading
from math import sqrt
from urllib.request import urlopen
import numpy as np

from secrets import get_host_color_map
from secrets import get_owner_host_map
from secrets import get_host_owner_map
from secrets import get_owner_color_map
from secrets import get_api_msg_template
from secrets import get_api_key
from secrets import is_mine


IPADDR_BASE = '192.168.0.{}'

COLOR_RESET   = '\033[0m'
COLOR_RED     = '\033[31m'
COLOR_GREEN   = '\033[32m'
COLOR_YELLOW  = '\033[33m'
COLOR_BLUE    = '\033[34m'
COLOR_MAGENTA = '\033[35m'
COLOR_CYAN    = '\033[36m'
COLOR_GRAY    = '\033[37m'
COLOR_WHITE   = '\033[39m'

SCREEN_CLEAR  = chr(27) + "[2J"

HOST_OWNER_MAP = get_host_owner_map()


def get_host_replacement():
	d = {}
	for x in range(256):
		addr = IPADDR_BASE.format(x)
		d[addr] = addr
	with open('/etc/hosts', 'r') as file:
		for line in file:
			parts = line.split()
			if len(parts) >= 2:
				d[parts[0]] = parts[1]
	return d
HOSTS = get_host_replacement()

def get_color(host):
	color_map = get_host_color_map()
	if host in color_map:
		return color_map[host]
	else:
		return COLOR_WHITE

def apply_color(host):
	return get_color(host) + host + COLOR_RESET

def main():
	try:
		for line in sys.stdin:
			line = line.strip()
			if line:
				parts = line.split()
				if len(parts) >= 8 and parts[7] in HOSTS and parts[4].startswith('query'):
					query = parts[5]
					host = HOSTS[parts[7]]
					if HOST_OWNER_MAP[host] != 'Brandon':
						print(apply_color(host), query)
	except KeyboardInterrupt:
		print('INTERRUPTED')
		pass
	finished = True


if __name__ == '__main__':
	main()
