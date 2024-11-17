# Use slim Python image
FROM python:3.10.0-slim

# Set working directory
WORKDIR /app

# Copy requirements and Prisma files first
COPY requirements.txt .
COPY prisma/ ./prisma/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

ENV PRISMA_BINARY_TARGETS_PATH=/tmp/prisma-binaries
RUN mkdir -p /tmp/prisma-binaries

ENV PRISMA_CACHE_DIR=/tmp/prisma-cache
RUN mkdir -p /tmp/prisma-cache

RUN apt-get update -y && apt-get install -y openssl



# Install and generate Prisma client
RUN pip install prisma
RUN prisma generate

# Copy Prisma query engine to /tmp for use in Lambda
RUN cp $(find /root/.cache/prisma-python/binaries -name 'query-engine-*') /tmp/prisma-query-engine

# Set environment variable for Prisma query engine binary location
ENV PRISMA_QUERY_ENGINE_BINARY=/tmp/prisma-query-engine


# Copy your FastAPI application and entry script
COPY app/ ./app/
COPY entry.sh .
RUN chmod +x entry.sh

# Expose the port FastAPI will run on (for local testing)
EXPOSE 8080

# Use entry script as entrypoint
ENTRYPOINT [ "./entry.sh" ]

