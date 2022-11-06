#!/usr/bin/env bash

# This script loads the newest backup into the local database,
# pseudonymizes the data and pushes it to the GitLab registry.
#
# Currently, it is configured to work on Daniel's computer.

set -e

# Checkout master to apply migrations that are available in all environments only

git checkout master

# Delete development database and load new production data

docker-compose up -d db

docker-compose run -v $HOME/backups/langify:/backups:ro db bash -c \
  "dropdb -h db -U postgres --if-exists ellen4all \
  && createdb -h db -U postgres ellen4all \
  && (pg_restore -d ellen4all -h db -U postgres -O /backups/latest_langify_production.sql || true)"

# Pseudonymize data

docker-compose run django bash -c \
  "./manage.py migrate \
  && ./manage.py pseudonymize \
  && ./manage.py test --settings=langify.settings_test --tag run-no-test -k"

# Export database

docker-compose run -v $PWD/docker/sql:/export db bash -c \
  "pg_dump -h db -U postgres --format=custom --file=/export/ellen4all.sql ellen4all \
  && pg_dump -h db -U postgres --format=custom --file=/export/test_ellen4all.sql test_ellen4all"

# Build & push PostgreSQL images with pseudonymized data

docker-compose -f docker-compose.yml -f docker/docker-compose.build.yml build builddb buildtestdb

docker-compose -f docker-compose.yml -f docker/docker-compose.build.yml push builddb buildtestdb
