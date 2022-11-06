#!/usr/bin/env bash

# This script dumps the production database on the server and downloads it.
# You can use crontab to run it automatically.
# See https://ole.michelsen.dk/blog/schedule-jobs-with-crontab-on-mac-osx.html

destination="langify@host1.codethink.de"
port=22007
now=$(date +"%Y-%m-%d-%H-%M-%S-%Z")
path="$HOME/backups/langify"
file="langify_production-$now.sql"
target="$path/$file"

echo "Starting to dump database..."
ssh -p $port $destination "pg_dump langify_production --format=custom --file=production.sql"

echo "Starting download..."
mkdir -p $path
scp -P $port $destination:./production.sql $target
ln -fs $file $path/latest_langify_production.sql
echo "Downloaded backup to $target"
