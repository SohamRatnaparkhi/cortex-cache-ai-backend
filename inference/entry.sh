#!/bin/bash
set -e

# Debug: Print current paths and environment
python -c "import sys; print('Python paths:', sys.path)"
python -c "import os; print('PYTHONPATH:', os.environ.get('PYTHONPATH'))"
python -c "import os; print('PATH:', os.environ.get('PATH'))"
python -c "import os; print('PRISMA_QUERY_ENGINE_BINARY:', os.environ.get('PRISMA_QUERY_ENGINE_BINARY'))"

# Ensure Prisma directories exist and have correct permissions
mkdir -p /app/.prisma/binaries
mkdir -p /app/.prisma/cache

# Verify query engine exists
if [ -f "$PRISMA_QUERY_ENGINE_BINARY" ]; then
    echo "Query engine found at $PRISMA_QUERY_ENGINE_BINARY"
    ls -l "$PRISMA_QUERY_ENGINE_BINARY"
else
    echo "Query engine not found at $PRISMA_QUERY_ENGINE_BINARY"
    exit 1
fi

if [ -z "${AWS_LAMBDA_RUNTIME_API}" ]; then
    # If not in Lambda environment, run local server
    exec uvicorn app.main:app --host 0.0.0.0 --port 8080
else
    # In Lambda environment, run handler
    exec python -m awslambdaric app.main.handler
fi