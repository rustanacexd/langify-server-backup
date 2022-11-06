# Langify Django project

Some information on the backend.

## URLs

- http://localhost:8001/admin/
- http://localhost:8001/api/docs/
- http://localhost:8001/api/
- http://localhost:8001/page/stats/

### External APIs

- [Ellen White Estate](https://a.egwwritings.org/)
- [Mailjet](https://dev.mailjet.com/guides/)
- [Newsletter2Go](https://documenter.getpostman.com/view/5017539/RWTg1N6k)
- [DeepL](https://www.deepl.com/docs-api.html)
- [Slack](https://api.slack.com/)

## Docker

Docker is our choice to set up the development environment.

### Django config

Copy `config.example.ini` as `config.ini` and adjust the values.

You should set:

`ALLOWED_HOSTS: 127.0.0.1 localhost django`

The database section should look like:

```ini
[database]
USER: postgres
PASSWORD:
HOST: db
PORT: 5432
ENGINE: django.db.backends.postgresql_psycopg2
NAME: ellen4all
```

For Redis to work:

```ini
CACHE_PORT: 6379
PERSISTENT_PORT: 6379
```

For Email to work:
```ini
[email]
default_from_email = Ellen4all <notifications@ellen4all.org>
host = mail.codethink.de
host_password = DyOcJanM9BXjBjr9LvudvcV8
host_user = notifications@ellen4all.org
default_to_emails = Ellen4all <notifications@ellen4all.org>
```

### Run development services

1. `docker-compose up` or leaner `docker-compose up django nuxt`
2. Visit the admin panel at http://localhost:8001/admin/ and the site at http://localhost:3000
3. To exit: Ctl-C or `docker-compose down`

### Useful commands

#### Django

`docker-compose run django bash` -> then you can run management commands (e.g. `./manage.py shell`)

`docker-compose run django python manage.py shell` (or `migrate`, etc.)

`docker-compose run django python manage.py test --settings=langify.settings_test --exclude selenium --exclude online --exclude slow -k`

#### PostgreSQL

`docker-compose run db psql -h db -U postgres`

`docker-compose run db createdb ellen4all -h db -U postgres`

`docker-compose run -v path/to/your/backup:/backup db pg_restore -h db -d ellen4all -O /backup/ellen4all.sql -U postgres` (Reported errors can normally be ignored.)

### Update the database with pseudonymized production data

When you run `docker-compose up` for the first time, a volume ending with `postgresql` and a database with pseudonymized production data are created.

If you want to refresh the data, look for the name of your volume (`docker volume ls`) and run `docker volume rm <name>`.
(You might have to remove containers first.
You can run `docker-compose down --remove-orphans && docker container prune`.)
The next time you run `django` (or `db`) you will have a fresh database.

If you want to backup your database first, you could run:

`docker-compose run -v ellen4all-db-backup:/backup db tar -zcvf /backup/postgres.tar.gz /var/lib/postgresql/data/`

To restore it: `docker-compose run -v ellen4all-db-backup:/backup db bash -c "rm -r /var/lib/postgresql/data/* && tar -zxvf /backup/postgres.tar.gz"`

You might have to migrate the database:

1. `docker-compose up -d db`
2. `docker-compose run django python manage.py migrate`

Now you can start Django and login with user and password *admin*. All other users have the password *pw*.

### Add/update Python packages

`docker-compose run django pipenv install <package name>` to install a package. Now you can use it.

Just before you commit your changes, run `docker-compose run django ./update_images.py` and add the chagned files to your commit. Note that `docker-compose up` will try to download a new image the next time you run it.

### Debugging

If you want to debug (e.g. with `import ipdb; ipdb.set_trace()`), run Django with `docker-compose run --service-ports django`. Note that the frontend can't connect in this case.

Possible alternative: https://medium.com/@vladyslav.krylasov/how-to-use-pdb-inside-a-docker-container-eeb230de4d11

## Checklist for commits

See *mr_checklist.txt*.

## Code style

1. Black formatting (see `pyproject.toml`)
2. Tuples are preferable over lists
3. Use [f-strings](https://realpython.com/python-f-strings/) where possible and appropriate (doesn't work with `gettext`)
4. Use `.format()` otherwise
5. Use third person and simple present in docstrings
6. Define a variable if a code with `return` doesn't fit into one line
7. Variable names: `queryset`
8. Put string into parentheses if it doesn't fit into one line
9. Use `pk`, not `id` where appropriate
10. It is better to assign objects than IDs if it doesn't cause another DB hit (`segment=segment` vs. `segment_id=segment.pk`)
11. Do not edit database schema migrations (except for linting)
12. Comments: Capitalize the first word, don't end with a period if it is one sentence only
13. API serializers should be uniform for each database model throughout the whole API as far as possible (the presence of fields might differ though)

### Tests

1. Assertions have this order: `assertEqual(received, expected)`
2. `res` is the variable for the response of the test client
3. `self.obj` is the database object that is tested in a test class
4. `self.url` is the URL that is tested in a test class
5. Test each endpoint or function with database queries once with `assertNumQueries()` and check if the number of queries can be minimized
6. Factories should generally only set fields that are required

### Automated Python style checks

Run this to check with **flake8** automatically (assumes it is installed with *pipenv*):

```bash
pipenv run flake8 --install-hook git
git config --bool flake8.strict true
```

More information [here](http://flake8.pycqa.org/en/latest/user/using-hooks.html).

Information on how to integrate **Black** in your editor [here](https://github.com/ambv/black#editor-integration).

Find out about **isort** [editor integration](https://github.com/timothycrosley/isort/wiki/isort-Plugins) and [git hooks](https://isort.readthedocs.io/en/latest/#git-hook).

## Cronjobs

* `delete_comments` to delete comments where the deadline passed
* `unlock_segments` to release all translated segments (with 3 min delay)
* `update_headings` to update the tables of contents, book and chapter statistics

Prefix the commands by `$ docker-compose run django python manage.py <command>` to run them.

## Redis

It is optional in development environments.

Redis is used for

- caching
- asynchroneous tasks (Celery), i.e.
  - deleting comments with TTL (time to live) set
  - running machine translation (see "periodic tasks" in the admin area)

- You can explicitly start Celery with `docker-compose up celery beat`

To see what happens, run `redis-cli --stat`.

## Jupyter Notebooks

Some often used commands are found in notebooks. You can use them by running

`docker-compose run django python manage.py shell_plus --notebook`,

then opening the notebook you need and finally run the cell. (Please, don't
commit changes when possible.)

As an alternative, you can copy the code from the `ipynb` files and use the
shell to run it:

`docker-compose run django python manage.py shell_plus`

### Production

Note that this doesn't work in production. Here, you should `cd` to the
`django` folder and run `.venv/bin/python manage.py shell`. Then you have to
import everything you need first. (`shell_plus` imports some stuff for you.)

## Tests

`docker-compose run django python manage.py test --settings=langify.settings_test --exclude selenium --exclude online --exclude slow -k`

**Important:** Always use the test settings (they are included in the command above) when testing in production! Otherwise, you use the production cache for tests.

In order to use the Selenium tests you have to install the
[drivers](https://seleniumhq.github.io/docs/wd.html#quick_reference) you want.
~Then add to your test command e.g.: `--selenium=firefox,chrome`.~ Currently
only Firefox/geckodriver supported.

You can create your own file called `frontend.py` or what ever you prefer in `panta/tests/`. Then you implement your Selenium tests. ~See `browser.py` as example.~ Run them as: `manage.py test … panta.tests.frontend`

### Information

* Debugging: https://docs.python.org/3/library/pdb.html
* Selenium: http://selenium-python.readthedocs.io/
* Available browsers:
  https://github.com/SeleniumHQ/selenium/tree/master/py/selenium/webdriver

## Errors

```
django.db.utils.ProgrammingError: column some.column does not exist
```

-> You should migrate your database (something like `manage.py migrate`).

```
  File "./manage.py", line 14
    ) from exc
         ^
SyntaxError: invalid syntax
```

-> You forgot to activate the venv.

```
atomic_caches = self.atomic_caches[db_alias].pop().values()

Exception Type: IndexError
Exception Value: pop from empty list
```

-> Run `python manage.py invalidate_cachalot`.

## Data

This section is for development only.

### Use production data

For this you need access to the server. You can get a database copy with `bash backup.sh` or do it manually:

#### Server

`pg_dump langify_production --format=custom --file=$HOME/production.sql`

#### Local

Download the SQL file, e.g.

`scp -P <port> <user>@<host>:/path/to/home/production.sql $HOME`

and then

`pg_restore -d your_database_name -O path/to/your_restore_file.sql`.

Your database should be empty. (See above how to create one.)

### Data pseudonymization

Run this command to pseudonymize the data:

`python manage.py pseudonymize`

Users have the password `pw` except for *admin* (super user) who has the password `admin`.

## Update staging with pseudonymized production data

Follow these steps:

_Check the scripts before you run them on your machine!_

Execute in `./` (project root)

1. `bash backup.sh`
2. `bash create_db_images.sh` You should interrupt when it uploads the Docker image to GitLab.
3. `docker-compose run -v $PWD:/django db bash -c "pg_dump -h db -U postgres ellen4all --format=custom --file=/django/pseudonymized.sql"`
4. `scp -P 22007 pseudonymized.sql langify@host1.codethink.de:./`
5. `ssh -p 22007 langify@host1.codethink.de "dropdb langify_staging && createdb langify_staging && pg_restore -d langify_staging -O pseudonymized.sql; staging/django/.venv/bin/python staging/django/manage.py invalidate_cachalot"`

## Django Bash completion

https://github.com/django/django/blob/master/extras/django_bash_completion

## Alternatives to the command `pipenv`

You can also use the following instead of `pipenv run python`:
* `pipenv shell` and then run the python files just with a `./` prefix, e.g. `./manage.py …` (type `exit` in order to leave the `pipenv` shell)
* `.venv/bin/python`, this gives you more flexibility because you don't have to be in the project dir: `path/to/repository/django/.venv/bin/python`

## Deployment

`build.py` returns a POSIX conform exit code. Please restore the old files if it isn't `0`. An error message will be sent to the `DEFAULT_TO_EMAILS` addresses specified in `config.ini` (if email settings are provided) in this case.

`REMOTE_ADDR` has to be configured as the client's IP address.

--------------------------------------------------------------------------------

## Some old stuff

### Installation for development

… if you use Docker, you can skip most of this.

#### 1. Django config file

Copy `config.example.ini` as `config.ini` and adjust the values.

#### 2. pipenv

[Install](https://docs.pipenv.org/install/) `pipenv` (similar to `npm`), e.g. `$ brew install pipenv`.

You should add `PIPENV_VENV_IN_PROJECT` to your environment variables.

#### 3. PostgreSQL

(This is required because we use some PostgreSQL specific fields and commands.)

1. Install [Postgres.app](http://postgresapp.com/) (for Mac, recommended) or use [another option](https://www.postgresql.org/download/macosx/)
2. Using Postgres.app: `$ export PATH=$PATH:/Applications/Postgres.app/Contents/Versions/{{version}}/bin` (this might also work: `$ export PATH=$PATH:/Applications/Postgres.app/Contents/Versions/latest/bin`, or as described in manual)
3. ```bash
   $ psql
   username=# CREATE DATABASE langify;
   ```
   <kbd>ctrl-D</kbd> (or `\q`)

   (in order to delete it: `username=# DROP DATABASE langify;`)

4. Update your config.ini:
   ```ini
   [database]
   USER: username
   PASSWORD:
   HOST: localhost
   PORT: 5432
   ENGINE: django.db.backends.postgresql_psycopg2
   NAME: langify
   ```

#### 4. Redis

It is optional in development environments.

Redis is used for

- caching
- asynchroneous tasks (Celery), i.e.
  - deleting comments with TTL (time to live) set
  - running machine translation (see "periodic tasks" in the admin area)

1. Install redis e.g. with Homebrew
2. Run `redis-server` in your termial
3. Update your config.ini (you can find the port in the termial, default is 6379)

- From now on, Redis is used for caching
- For the asynchroneous tasks you have to run another command: `pipenv run celery-worker`

To see what happens, run `redis-cli --stat` in another terminal.

### Build for development

You can use a package that is also used on production:

1. Install it with `git submodule update --init`
2. Run `$ python3 django/up-to-date/build.py` (creates a virtual env, installs packages, runs tests, migrates database and collects static files if not debug)

Alternatively, you can use some npm commands to build it together with the frontend or use the Django commands directly.

You can build the frontend with `pipenv run npm-install`.

Now you probalby have a working environment but without data. If you need some, please contact Daniel.

### Development servers

Run in different terminal windows:

1. `pipenv run django-server`
2. `pipenv run nuxt-server`
3. If you need Celery: `pipenv run celery-worker`

Besides that, there are a hand full of useful commands listed in `Pipfile` under section `scripts` you can use in development.

### Import a DOCX work

```bash
$ pipenv run python manage.py runscript import_work_fresh_db --script-args /path/to/your/import.zip # Does all the create's and import's below

#### Alternatively you can select what to do by using:

$ pipenv run python manage.py runscript create_admin   # username and password = admin

$ pipenv run python manage.py runscript create_egw # Creates an author
$ pipenv run python manage.py runscript create_estate # Creates a trustee
$ pipenv run python manage.py runscript create_licence # Creates a licence
$ pipenv run python manage.py runscript import_work --script-args da # Import Desire of Ages
$ pipenv run python manage.py runscript delete_all_works # Deletes all works (including segments and histories)
```

If you need something else you may use the factories (data created randomly):

```bash
$ pipenv run python manage.py shell
```

```python
>>> from panta import factories
>>> works = factories.create_work()
>>> works['original']
<OriginalWork: Lorem ipsum>
>>> works['translations']
[<TranslatedWork: Lorem ipsum 1>, <TranslatedWork: Lorem ipusm 2>, <TranslatedWork: Lorem ipsum 3>]
>>> # or create content for specific models (with dependencies):
>>> trustee = factories.TrusteeFactory()
>>> trustee
<Trustee: Lorem ipsum Inc.>
>>> # or create multiple objects at once:
>>> factories.TranslatedSegmentFactory.create_batch(100)
>>> quit() # or ctrl-D
```

`create_work` generates a work with translations. You can optionally specify these settings:

- `segments` of the work, default `500`
- `translations` as total count, default `3`
- `languages` to be used (randomly), default `base.constants.LANGUAGES` if supported
- `completeness` of the translations as min, max in %, default `(0, 100)`
- more key word arguments to customize the original work factory

See `django/panta/factories.py` for all factories to be used. All models should be represented there.

More info: http://factoryboy.readthedocs.io/en/latest/introduction.html

### Super user

Create one with `$ pipenv run python manage.py runscript create_admin` (for development only) or `$ pipenv run python manage.py createsuperuser`

### HTML

You can find the used HTML definitions in `django/panta/constants.py`. For conversions see `django/panta/conversion/<specific_file>.py:MAPPING`.

### Authentication

* Django uses a http only session cookie to determine authentication.
  * No extra implementation necessary.
  * If the session expired requests to the back end where authentication
    required will response with permission denied. (ToDo: How to determine if a
    session expired or the current user just isn't allowed to view the
    content? - Django can send a different reason: either `authentication
    needed` (i.e. user not authenticated) or `no permission` (i.e. user
    authenticated but has not required permissions).)
* Django sends an additional headers when a user logged in or out.
