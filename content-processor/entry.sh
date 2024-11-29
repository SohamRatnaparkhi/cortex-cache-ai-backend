#!/bin/bash
set -e

# Ensure Prisma directories exist and have correct permissions
mkdir -p /app/.prisma/binaries
mkdir -p /app/.prisma/cache


if [ -z "${AWS_LAMBDA_RUNTIME_API}" ]; then
    # If not in Lambda environment, run local server
    exec uvicorn app.main:app --host 0.0.0.0 --port 8080
else
    # In Lambda environment, run handler
    exec fastapi run app/main.py --port 8080 --workers=4
fi