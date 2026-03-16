# AI Prompt: I am converting my express travel app into FastApi, my files are attach that i describe most of the thing of how i do code

# Initialize new project (creates pyproject.toml, main.py, etc.)

## An extremely fast Python package and project manager, written in Rust.

```bash
https://docs.astral.sh/uv/
```

uv init

# Create virtual environment

uv venv

# Activate virtual environment

source .venv/bin/activate

# Add/install dependencies

uv add fastapi uvicorn[standard] sqlmodel alembic bcrypt email-validator gunicorn psycopg2-binary python-jose[cryptography]

# Install dependencies (sync from lock file)

uv sync

# Run FastAPI app

uv run -- uvicorn src.main:app --reload

# apt install make for run command ease (for linux)

- create Makefile and define command, follow the syntax must
  make run
  make activate
  make head
  make generate

# install from pyproject.toml

uv pip install -r pyproject.toml

# Update lock file without installing

uv lock

# Clean install (remove unused and reinstall)

uv sync --clean

# alembic

uv add alembic

# if not

source .venv/bin/activate

# for psql install

uv pip install psycopg2-binary

# Alembic

```bash
#📌 Basic
alembic init migrations # create migrations folder (first time only)
alembic current # show current DB revision
alembic show head # show the latest migration in code
alembic history # list all migrations

#📌 Creating migrations
alembic revision -m "add new table" # create empty migration
alembic revision --autogenerate -m "msg" # auto-detect model changes

#📌 Upgrading & downgrading
alembic upgrade head # apply all migrations to latest
alembic upgrade +1 # apply next migration
alembic upgrade <revision_id> # upgrade to specific revision

alembic downgrade -1 # revert last migration
alembic downgrade base # revert all migrations
alembic downgrade <revision_id> # downgrade to specific revision

#📌 Stamping (force set revision without running migrations)
alembic stamp head # mark DB as up-to-date
alembic stamp <revision_id> # force DB revision
```

# Migration env

```py
from sqlmodel import SQLModel
from src.config import DATABASE_URL
from src.api import models


config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = SQLModel.metadata

```

#

## http://localhost:8000/docs

# Git

```shell
# For a pull with merge you just need this command:
git pull --no-rebase
```
