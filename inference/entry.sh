#!/bin/bash
export PRISMA_CACHE_DIR=/tmp
if [ -z "${AWS_LAMBDA_RUNTIME_API}" ]; then
    # If not in Lambda environment, run local server
    exec uvicorn app.main:app --host 0.0.0.0 --port 8080
else
    # In Lambda environment, run handler
    exec python -m awslambdaric app.main.handler
fi