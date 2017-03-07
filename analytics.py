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


queries_mine = {}
queries_other = {}
data_lock = threading.Lock()


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


def log_query(host, query):
	global data, data_lock
	global queries_mine, queries_other
	data_lock.acquire()

	if is_mine(host):
		if query not in queries_mine:
			queries_mine[query] = 1
		else:
			queries_mine[query] = 1 + queries_mine[query]
	else:
		if query not in queries_other:
			queries_other[query] = 1
		else:
			queries_other[query] = 1 + queries_other[query]

	data_lock.release()


class Printer(threading.Thread):

	def __init__(self):
		threading.Thread.__init__(self, name='Printer', daemon=True)

	def run(self):
		while True:
			now = time.time()
			self.print_stats()
			time_duration = time.time() - now
			time.sleep(2)

	def print_stats(self):
		global data, data_lock
		global queries_mine, queries_other
		data_lock.acquire()

		print(SCREEN_CLEAR)
		print('\nmine')
		queries_mine_sorted = sorted(queries_mine.items(), key=operator.itemgetter(1), reverse=True)
		for query, count in queries_mine_sorted[:min(12, len(queries_mine_sorted))]:
			print('{:7}  --  {}'.format(count, query))
		print('\nother')
		queries_other_sorted = sorted(queries_other.items(), key=operator.itemgetter(1), reverse=True)
		for query, count in queries_other_sorted[:min(12, len(queries_other_sorted))]:
			print('{:7}  --  {}'.format(count, query))

		data_lock.release()


class HostUpdater(threading.Thread):

	def __init__(self):
		threading.Thread.__init__(self, name='HostUpdater', daemon=True)

	def run(self):
		global HOSTS
		while True:
			HOSTS = get_host_replacement()
			time.sleep(60)


def main():
	printer = Printer()
	printer.start()
	updater = HostUpdater()
	updater.start()
	try:
		for line in sys.stdin:
			line = line.strip()
			if line:
				parts = line.split()
				if len(parts) >= 8 and parts[7] in HOSTS and parts[4].startswith('query'):
					query = parts[5]
					host = HOSTS[parts[7]]
					log_query(host, query)
	except KeyboardInterrupt:
		print('INTERRUPTED')
		pass


if __name__ == '__main__':
	main()
