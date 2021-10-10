#!/bin/bash

set -e

g++ -std=c++11 test.cpp -o test_cpp
./test_cpp
rm test_cpp
