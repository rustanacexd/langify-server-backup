#!/bin/bash

# These commands should be run from time to time.

# Remove stale files
./manage.py collectstatic --clear
