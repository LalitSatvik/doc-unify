#!/bin/sh
# Production start command (Render, or any host that doesn't want the
# dev CMD's --reload). Kept as a real script rather than an inline
# shell string in render.yaml, since how a chained "a && b" command
# survives a platform's own command-field tokenizing isn't reliable.
set -e
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
