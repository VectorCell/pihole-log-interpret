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

finished = False


# key=host, value=dict(key=query, value=count)
queries = {}
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
	global queries

	if query[0].isdigit() or query[::-1].startswith('.arpa'[::-1]):
		return

	data_lock.acquire()
	if host not in queries:
		queries[host] = {}
	if query not in queries[host]:
		queries[host][query] = 1
	else:
		queries[host][query] = 1 + queries[host][query]
	data_lock.release()


class Printer(threading.Thread):

	def __init__(self):
		threading.Thread.__init__(self, name='Printer', daemon=True)

	def run(self):
		while not finished:
			now = time.time()
			self.print_stats()
			time_duration = time.time() - now
			time.sleep(2)

	def print_stats(self):
		global data, data_lock
		global queries
		data_lock.acquire()

		print(SCREEN_CLEAR)
		owner_host_map = get_owner_host_map()
		owners = sorted(owner_host_map.keys())
		for owner in owners:
			print(get_owner_color_map()[owner] + owner + COLOR_RESET)
			accum = {}
			for host in owner_host_map[owner]:
				if host in queries:
					for query in queries[host]:
						if query not in accum:
							accum[query] = queries[host][query]
						else:
							accum[query] = queries[host][query] + accum[query]
			accum_sorted = sorted(accum.items(), key=operator.itemgetter(1), reverse=True)
			accum_sorted_top = accum_sorted[:min(10, len(accum_sorted))]
			for query, count in accum_sorted_top:
				print('{:8} -- {}'.format(count, query))

		#print('\nmine')
		#queries_mine_sorted = sorted(queries_mine.items(), key=operator.itemgetter(1), reverse=True)
		#for query, count in queries_mine_sorted[:min(12, len(queries_mine_sorted))]:
		#	print('{:7}  --  {}'.format(count, query))
		#print('\nother')
		#queries_other_sorted = sorted(queries_other.items(), key=operator.itemgetter(1), reverse=True)
		#for query, count in queries_other_sorted[:min(12, len(queries_other_sorted))]:
		#	print('{:7}  --  {}'.format(count, query))

		data_lock.release()


class HostUpdater(threading.Thread):

	def __init__(self):
		threading.Thread.__init__(self, name='HostUpdater', daemon=True)

	def run(self):
		global HOSTS
		while not finished:
			HOSTS = get_host_replacement()
			time.sleep(60)


def main():
	global finished
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
	finished = True


if __name__ == '__main__':
	main()
