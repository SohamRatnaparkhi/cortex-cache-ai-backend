# Use slim Python image
FROM python:3.10.0-slim

# Set working directory
WORKDIR /app

# Create a non-root user
RUN useradd -m -u 1000 appuser

# Install system dependencies
RUN apt-get update -y && \
    apt-get install -y openssl dos2unix curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set up environment variables
ENV HOME=/home/appuser
ENV PYTHONUSERBASE=/home/appuser/.local
ENV PYTHONPATH=/home/appuser/.local/lib/python3.10/site-packages:/app
ENV PATH=/home/appuser/.local/bin:$PATH
# ENV PRISMA_BINARY_TARGETS_PATH=/app/.prisma/binaries
# ENV PRISMA_CACHE_DIR=/app/.prisma/cache
# # Set the query engine path to a writable location
# ENV PRISMA_QUERY_ENGINE_BINARY=/app/.prisma/engine

# Create necessary directories and set permissions
RUN mkdir -p /app/.prisma/binaries && \
    mkdir -p /app/.prisma/engine && \
    mkdir -p /app/.prisma/cache && \
    mkdir -p /home/appuser/.local/lib/python3.10/site-packages 


RUN chown -R appuser:appuser /app && \
    chown -R appuser:appuser /home/appuser

# Copy only the necessary files
COPY requirements.txt .
COPY app/ ./app/
COPY prisma/ ./prisma/
COPY entry.sh .

# Fix permissions and line endings
RUN dos2unix entry.sh && \
    chmod +x entry.sh && \
    chown -R appuser:appuser /app

# Switch to non-root user for installations
USER appuser

# Install Python dependencies including Prisma
RUN pip install --user awslambdaric mangum && \
    pip install --user -r requirements.txt && \
    pip install --user prisma

# Generate Prisma client and copy binary to permanent location
WORKDIR /app/prisma
RUN python -m prisma generate && \
    # Ensure the binary is copied to our specified location
    cp -r /home/appuser/.local/lib/python3.10/site-packages/prisma/binaries /app/.prisma/binaries && \
    chmod +x /app/.prisma/binaries && \
    # Ensure the query engine is copied to our specified location
    cp -r /home/appuser/.local/lib/python3.10/site-packages/prisma/engine /app/.prisma/engine && \
    chmod +x /app/.prisma/engine
# Switch back to app directory
WORKDIR /app

# Expose the port FastAPI will run on
EXPOSE 8080

# Use entry script as entrypoint
ENTRYPOINT ["./entry.sh"]