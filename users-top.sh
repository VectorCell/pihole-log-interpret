#!/bin/bash

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
dir=$(dirname $(readlink -f $DIR/$(basename "$0")))
cd $dir

if [ "$1" == "-n" ]; then
	cat log/* | ./users-top.py
else
	(cat log/*; tail -F /var/log/pihole.log) | ./users-top.py
fi
