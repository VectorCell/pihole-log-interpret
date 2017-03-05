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

IPADDR_BASE = '192.168.0.{}'


# key: hostname
# value: previous query time
host_log = {}
host_stats = {}
host_lock = threading.Lock()


time_threshold = 3.0
time_threshold_exceeded = False
time_duration = 0.0
time_durations = []
time_duration_max = 0.0


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


def send_msg(msg):
	message = msg.replace(' ', '%20')
	print("REFUSING TO SEND MESSAGE: {}".format(message))
	url = get_api_msg_template().format(message)
	try:			
		response = urlopen(url).read().decode('utf-8')
		print(response)
	except URLError as e:
		print(e)


def is_mine(host):
	return host in MINE

def get_color(host):
	color_map = get_host_color_map()
	if host in color_map:
		return color_map[host]
	else:
		return COLOR_WHITE

def apply_color(host):
	return get_color(host) + host + COLOR_RESET


def calc_mean(data):
	try:
		return sum(data) / len(data)
	except ZeroDivisionError:
		return -1

def calc_stddev(data, mean = None):
	try:
		if mean is None:
			mean = calc_mean(data)
		return sqrt(sum((x - mean) ** 2 for x in data) / len(data))
	except ZeroDivisionError:
		return -1

def calc_percentiles(data):
	if data:
		a = np.array(data)
		return [int(round(np.percentile(a, x), 0)) for x in range(10, 110, 10)]
	else:
		return []

def time_difference_readable(diff):
	hours = int(diff // (60 * 60))
	minutes = int((diff - hours * (60 * 60)) // 60)
	seconds = int(diff - hours * (60 * 60) - minutes * 60)
	values = []
	if hours:
		values.append('{} h'.format(hours))
	if minutes:
		values.append('{:2} m'.format(minutes))
	values.append('{:2} s'.format(seconds))
	return ', '.join(values)


def log_arrival(date, query, host, now):
	should_send_msg = False
	if host in host_log:
		time_since_last = now - host_log[host]
		if 'phone' in host and time_since_last > (2 * 60 * 60): # 2 hours
			should_send_msg = True
#	elif 'phone' in host:
#		should_send_msg = True
	elif host[0].isdigit():
		should_send_msg = True
	if should_send_msg:
		send_msg(host)


def log_host_activity(date, query, host):
	host_lock.acquire()
	now = time.time()
	if host in host_stats:
		host_stats[host].append(now - host_log[host])
		#if len(host_stats[host]) > 999:
		#	del host_stats[host][0]
	else:
		host_stats[host] = []
	log_arrival(date, query, host, now)
	host_log[host] = now
	host_lock.release()


class Printer(threading.Thread):

	def __init__(self):
		threading.Thread.__init__(self, name='Printer', daemon=True)

	def run(self):
		global time_threshold
		global time_threshold_exceeded
		global time_duration
		global time_durations
		global time_duration_max
		print('waiting on input...')
		while not host_log:
			time.sleep(0.1)
		while True:
			now = time.time()
			self.print_stats()
			time_duration = time.time() - now
			time_durations.append(time_duration)
			time_duration_max = max(time_duration, time_duration_max)
			if time_duration > time_threshold:
				if not time_threshold_exceeded:
					send_msg('calculation time threshold exceeded')
				time_threshold_exceeded = True
			time.sleep(2)

	def print_activity(self):
		host_lock.acquire()

		now = time.time()
		print(SCREEN_CLEAR)
		print(datetime.datetime.now().strftime('%Y-%b-%d %I:%M %p'))
		print()

		max_hostname_len = 0
		for hostname in host_log:
			max_hostname_len = max(max_hostname_len, len(apply_color(hostname)))
		sortedmap = sorted(host_log.items(), key=operator.itemgetter(1), reverse=True)

		for hostname, last_query in sortedmap:
			time_readable = time_difference_readable(now - last_query)
			format_str = '{:' + str(max_hostname_len) + 's} {}'
			print(format_str.format(apply_color(hostname), time_readable))

		host_lock.release()

	def print_stats(self):
		global time_threshold
		global time_threshold_exceeded
		global time_duration
		global time_durations
		global time_duration_count
		global time_duration_max
		host_lock.acquire()

		now = time.time()

		hosts = [key for key, val in sorted(host_log.items(), key=operator.itemgetter(1), reverse=True)]
		stats = [host_stats[host] for host in hosts]

		table = {host: {} for host in hosts}
		for host in hosts:
			table[host]['name'] = apply_color(host).replace('.local', '')
			table[host]['n'] = len(host_stats[host]) + 1
			table[host]['time'] = time_difference_readable(now - host_log[host])
			table[host]['mean'] = round(calc_mean(host_stats[host]), 1)
			table[host]['stddev'] = round(calc_stddev(host_stats[host], table[host]['mean']), 1)
			table[host]['percentiles'] = calc_percentiles(host_stats[host])
			if table[host]['mean'] < 0:
				table[host]['mean'] = '-'
			if table[host]['stddev'] < 0:
				table[host]['stddev'] = '-'
		for host in hosts:
			for key in table[host]:
				format_key = '_'.join((key, 'max'))
				if format_key not in table:
					table[format_key] = 0
					table['_'.join((key, 'format'))] = None
				table[format_key] = max(table[format_key], len(str(table[host][key])))
		for max_key in table:
			if '_max' in max_key:
				fmt_key = max_key.replace('_max', '_format')
				table[fmt_key] = '{:' + str(table[max_key]) + 's}'
				if fmt_key == 'n_format':
					table[fmt_key] = '{:' + str(table[max_key]) + '}'
		for max_key in table:
			if '_max' in max_key:
				fmt_key = max_key.replace('_max', '_format')
				table[fmt_key] = '{:>' + str(table[max_key]) + '}'

		TABLE_SEP = ' │ '
		TABLE_JUNC = '─┼─'
		print(SCREEN_CLEAR)
		print(datetime.datetime.now().strftime('%Y-%b-%d %I:%M %p'))
		print()
		if time_threshold_exceeded:
			print('{:26s} ({})'.format('WARNING: calculation time threshold exceeded!', round(time_threshold, 3)))
			print()
		if time_durations:
			time_duration_total = sum(time_durations)
			time_duration_mean = time_duration_total / len(time_durations)
			print('{:26s} {} s'.format('previous calculation time:', round(time_duration, 3)))
			print('{:26s} {} s'.format('mean calculation time:', round(time_duration_mean, 3)))
			print('{:26s} {} s'.format('max calculation time:', round(time_duration_max, 3)))
			print('{:26s} {} s'.format('total calculation time:', round(time_duration_total, 3)))
		print()
		print(table['name_format'].replace('>', '<').format(apply_color('host')), end='')
		print(TABLE_SEP, end='')
		print(table['n_format'].replace('>', '<').format('n'), end='')
		print(TABLE_SEP, end='')
		print(table['time_format'].replace('>', '<').format('t'), end='')
		print(TABLE_SEP, end='')
		print(table['mean_format'].replace('>', '<').format('μ'), end='')
		print(TABLE_SEP, end='')
		print(table['stddev_format'].replace('>', '<').format('σ'), end='')
		print(TABLE_SEP, end='')
		print(table['percentiles_format'].replace('>', '<').format('P'), end='')
		print()
		print(table['name_format'].format(apply_color('─' * (table['name_max'] - len(apply_color(''))))), end='')
		print(TABLE_JUNC, end='')
		print(table['n_format'].format('─' * table['n_max']), end='')
		print(TABLE_JUNC, end='')
		print(table['time_format'].format('─' * table['time_max']), end='')
		print(TABLE_JUNC, end='')
		print(table['mean_format'].format('─' * table['mean_max']), end='')
		print(TABLE_JUNC, end='')
		print(table['stddev_format'].format('─' * table['stddev_max']), end='')
		print(TABLE_JUNC, end='')
		print(table['percentiles_format'].replace('>', '<').format('─' * table['percentiles_max']), end='')
		print()
		for host in hosts:
			print(table['name_format'].replace('>', '<').format(table[host]['name']), end='')
			print(TABLE_SEP, end='')
			print(table['n_format'].format(table[host]['n']), end='')
			print(TABLE_SEP, end='')
			print(table['time_format'].format(table[host]['time']), end='')
			print(TABLE_SEP, end='')
			print(table['mean_format'].format(str(table[host]['mean'])), end='')
			print(TABLE_SEP, end='')
			print(table['stddev_format'].format(str(table[host]['stddev'])), end='')
			print(TABLE_SEP, end='')
			print(table['percentiles_format'].replace('>', '<').format(str(table[host]['percentiles'])), end='')
			print()
		host_lock.release()


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
					date = ' '.join(parts[:3])
					query = parts[5]
					host_lock.acquire()
					host = HOSTS[parts[7]]
					host_lock.release()
					log_host_activity(date, query, host)
	except KeyboardInterrupt:
		print('INTERRUPTED')
		pass


if __name__ == '__main__':
	main()
