#!/bin/bash

set -e

gcc test.c -o test_c
./test_c
rm test_c
