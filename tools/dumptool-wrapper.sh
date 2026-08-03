#!/bin/sh
# Wrapper script to run the installed dumptool package.
exec python3 -m dumptool "$@"
