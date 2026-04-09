#!/bin/bash
mkdir bin
gcc -fPIC -shared plant.c -o ./bin/libplant.so