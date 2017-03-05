#!/bin/bash

if [ ! -d log ]; then
	mkdir log
fi

stash="dne.log"
for num in {00000..99999}; do
	stash=pihole.${num}.log
	echo "checking $stash"
	if [ ! -e log/$stash ]; then
		echo "using $stash"
		break
	fi
done
mv log/pihole.log log/$stash

tail -F -n +0 /var/log/pihole.log \
	| tee log/pihole.log \
	| grep --color=always -E '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+|$' \
	| sed 's/31m/97m/g'
