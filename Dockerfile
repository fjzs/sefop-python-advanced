# =============================================================================
# Dockerfile — packages the SEFOP web app (FastAPI) as a single container image.
# =============================================================================
# CMD is a command executed at container start time.
# RUN is a command executed at container build time.
#
# This is a single-stage build (no multi-stage split into a "build" image and
# a "runtime" image): the project's own commenting convention prioritizes
# being readable by a data scientist over shaving image size, and a second
# stage is exactly the kind of extra indirection that trades away. If image
# size ever becomes a real problem, splitting the `pip install` step into its
# own build stage is the natural next move.

# Use the official slim Python image: smaller than the full "python:3.12"
# image, but still Debian-based (not Alpine), so compiled extensions like
# ortools and highspy — this project's MIP solvers — find the standard
# glibc/libstdc++ they were built against without extra system packages.
FROM python:3.12-slim

# Set working directory inside container
WORKDIR /app

# Copy dependency file first (better layer caching): as long as
# requirements.txt doesn't change, Docker reuses this layer instead of
# re-downloading every dependency on every build, even if src/ changed.
COPY requirements.txt .

# Install dependencies. --no-cache-dir keeps pip's download cache out of the
# image layer entirely, since nothing in this container will ever run `pip
# install` again after this step.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the packaging metadata and source code, then install this project
# itself in the same way local development does (see README.md's
# Installation section) — this is what makes `frameworks_and_drivers.cli`
# and `frameworks_and_drivers.web.main` importable as top-level packages
# without manual PYTHONPATH manipulation.
COPY pyproject.toml .
COPY src/ ./src
RUN pip install --no-cache-dir -e .

# Copy the sample data folder too, so `frameworks_and_drivers.cli` works
# out of the box inside the container the same way it does locally.
COPY data/ ./data

# Expose the port Uvicorn will use
EXPOSE 8000

# - Why uvicorn:
# Uvicorn is a lightweight, high-performance ASGI (Asynchronous Server Gateway
# Interface) web server for Python. It's the runtime that lets an async
# framework like FastAPI handle HTTP connections. This is the process that
# actually listens on a port and serves requests.
#
# - Why a single process, no --workers or gunicorn:
# The web app's in-memory adapter (adapters/web/in_memory_data_loader.py)
# stores each submitted problem only for the lifetime of that one request,
# inside that one process's memory. Multiple worker processes would each get
# their own copy of that memory, which is harmless here (nothing is shared
# across requests anyway) but not something worth the added complexity of a
# process manager for what is a reference/demo-scale app.
#
# - Why --host 0.0.0.0:
# Inside the container, 127.0.0.1 means "reachable only from inside this
# container." 0.0.0.0 means "listen on every network interface," which is
# what makes `docker run -p 8000:8000 ...` able to reach the server at all.
#
# - Why --port 8000:
# Must match the EXPOSE line above and whatever port `docker run -p` maps to
# on the host.
CMD ["uvicorn", "frameworks_and_drivers.web.main:app", "--host", "0.0.0.0", "--port", "8000"]
