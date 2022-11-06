#!/bin/bash
set -e

if [ -f /sql/ellen4all.sql ]; then
  createdb -U $POSTGRES_USER ellen4all
  pg_restore -d ellen4all -O /sql/ellen4all.sql -U $POSTGRES_USER
fi

createdb -U $POSTGRES_USER test_ellen4all
pg_restore -d test_ellen4all -O /sql/test_ellen4all.sql -U $POSTGRES_USER
