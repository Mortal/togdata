#!/bin/bash

set -euo pipefail

T="`date +%H:%M:%S`"
D="`date +%Y%m%d`"
DIR=data
mkdir -p "$DIR"
filename="$DIR/`date +%Y%m%d%H%M%S.json`"
curl -so "$filename" "\
https://webapp.rejseplanen.dk/bin/query.exe/mn\
y?\
look_minx=-3312240&look_maxx=26482682&look_miny=51886983&look_maxy=59631919&\
tpl=trains2json3&\
look_json=yes&performLocating=1&\
look_requesttime=$T&\
look_nv=get_ageofreport|yes|get_rtmsgstatus|yes|get_rtfreitextmn|yes|\
get_passproc|yes|zugposmode|0|\
interval|30000|intervalstep|10000|\
get_nstop|yes|get_pstop|yes|get_stopevaids|yes|tplmode|trains2json3|\
cats|001,007,008,009,014,015,016,039,040,048,057,003,004,005,030,031,099,006,002,097,098,029&\
interval=30000&intervalstep=10000&&ts=$D&"
python parse.py "$@" "$filename"
