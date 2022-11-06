# From https://www.caktusgroup.com/blog/2017/03/14/production-ready-dockerfile-your-python-django-app/

# Using a Debian- and glibc-based image, because I found an inconvenient workaround was required for musl libc's strftime() implementation
FROM python:3.6-slim

ENV PYTHONUNBUFFERED=1
RUN mkdir -p /project/smedia

WORKDIR /project/django

# Add any static environment variables needed by Django or your settings file here:
ENV DJANGO_SETTINGS_MODULE=langify.settings

# Tell uWSGI where to find your wsgi file:
ENV UWSGI_WSGI_FILE=/project/django/langify/wsgi.py

# Base uWSGI configuration (you shouldn't need to change these):
ENV UWSGI_HTTP=:8001 UWSGI_MASTER=1 UWSGI_HTTP_AUTO_CHUNKED=1 UWSGI_HTTP_KEEPALIVE=1 UWSGI_UID=1000 UWSGI_GID=2000 UWSGI_LAZY_APPS=1 UWSGI_WSGI_ENV_BEHAVIOR=holy

# uWSGI static file serving configuration (customize or comment out if not needed):
ENV UWSGI_STATIC_MAP="/apps/=/project/static/apps/" UWSGI_STATIC_EXPIRES_URI="/apps/.*\.[a-f0-9]{12,}\.(css|js|png|jpg|jpeg|gif|ico|woff|ttf|otf|svg|scss|map|txt) 315360000"

# Deny invalid hosts before they get to Django (uncomment and change to your hostname(s)):
ENV UWSGI_ROUTE_HOST="^(?!localhost:8001$) break:400"

# uWSGI will listen on this port
EXPOSE 8001

COPY docker/bashrc $HOME/.bashrc

# Install packages needed to run your application (not build deps):
#   mime-support -- for mime types when serving static files
#   postgresql-client -- for running database commands
# We need to recreate the /usr/share/man/man{1..8} directories first because
# they were clobbered by a parent image.
RUN set -ex \
    && RUN_DEPS=" \
        libpcre3 \
        mime-support \
        postgresql-client \
    " \
    && seq 1 8 | xargs -I{} mkdir -p /usr/share/man/man{} \
    && apt-get update && apt-get install -y --no-install-recommends $RUN_DEPS \
    && apt-get install -y libpq-dev python-dev gcc git libpcre3-dev build-essential \
    && rm -rf /var/lib/apt/lists/*


SHELL ["/bin/bash", "-c"]

ARG version
ARG date
ENV LANGIFY_VERSION=$version BUILT_DATE=$date

# Copy your application code to the container (make sure you create a .dockerignore file if any large files or directories should be excluded)
ADD ./requirements.txt /project/django/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

ADD . /project/django

# TODO Find a better solution for this in production
RUN mkdir -p /project/django/logs && touch /project/django/logs/django_auth.log && chmod 777 /project/django/logs/django_auth.log

# Call collectstatic (customize the following line with the minimal environment variables needed for manage.py to run):
RUN set -a && \
    source default.env && \
    set +a && \
    export DEBUG=false && \
    python manage.py collectstatic --noinput;

# Number of uWSGI workers and threads per worker (customize as needed):
ENV UWSGI_WORKERS=2 UWSGI_THREADS=4

# Uncomment after creating your docker-entrypoint.sh
# ENTRYPOINT ["/code/docker-entrypoint.sh"]

# Start uWSGI
CMD ["uwsgi", "--show-config"]
