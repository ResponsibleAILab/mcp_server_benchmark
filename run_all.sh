#!/bin/bash
# run_all.sh - run bare-metal and container scripts 10 times

for i in {1..10}
do
    echo "============================="
    echo "Run $i of 10 — Bare Metal"
    echo "============================="
    ./run_baremetal_ext.sh 8 32 64 128

    echo "============================="
    echo "Run $i of 10 — Container"
    echo "============================="
    ./run_container_ext.sh 8 32 64 128
done