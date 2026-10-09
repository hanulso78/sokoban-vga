#!/bin/sh
# 회귀 시험: test/k_*.txt 시나리오를 원본(에뮬레이터)과 옮긴 C 로 돌려 대조한다.
#   원판 빌드(hosttest.exe) 는 CGA 와 Tandy, 개선판 빌드(hostvga.exe) 는 CGA 로.
cd "$(dirname "$0")/.."
export PYTHONIOENCODING=utf-8
P=/c/python-3.12.10-embed-amd64/python.exe
fail=0
for f in test/k_*.txt; do
    for run in "hosttest.exe c" "hosttest.exe t" "hostvga.exe c"; do
        set -- $run
        r=$(SKBHOST=$1 $P tools/difftest.py $2 "$(cat $f)" x | head -1)
        printf '%-20s %-14s %s\n' "$(basename $f)" "$1 $2" "$r"
        case "$r" in 같다*) ;; *) fail=1 ;; esac
    done
done
exit $fail
