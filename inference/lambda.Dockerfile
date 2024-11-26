# Use AWS Lambda Python 3.10 base image
FROM public.ecr.aws/lambda/python:3.10

# Copy Lambda adapter
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.8.4 /lambda-adapter /opt/extensions/lambda-adapter

# Install Node.js 16 and system dependencies
RUN yum install -y openssl curl
RUN curl -sL https://rpm.nodesource.com/setup_16.x | bash -
RUN yum install -y nodejs
RUN node -v && npm -v
RUN yum clean all
RUN rm -rf /var/cache/yum

# Set up environment variables for Prisma
# ENV PRISMA_BINARY_TARGETS_PATH=${LAMBDA_TASK_ROOT}/.prisma/binaries
# ENV PRISMA_CACHE_DIR=${LAMBDA_TASK_ROOT}/.prisma/cache
# ENV PRISMA_QUERY_ENGINE_BINARY=${LAMBDA_TASK_ROOT}/.prisma/engine/query-engine

# Create necessary directories
RUN mkdir -p ${LAMBDA_TASK_ROOT}/prisma && \
    mkdir -p ${LAMBDA_TASK_ROOT}/app && \
    mkdir -p ${LAMBDA_TASK_ROOT}/.prisma/binaries && \
    mkdir -p ${LAMBDA_TASK_ROOT}/.prisma/engine && \
    mkdir -p ${LAMBDA_TASK_ROOT}/.prisma/cache && \
    chmod -R 755 ${LAMBDA_TASK_ROOT}

# copy cached Prisma binaries from root/.cache


# Copy application files
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
COPY prisma/ ${LAMBDA_TASK_ROOT}/prisma/
COPY app/ ${LAMBDA_TASK_ROOT}/app/

# Install Python dependencies and Prisma
RUN pip install -r ${LAMBDA_TASK_ROOT}/requirements.txt && \
    pip install prisma

# Generate Prisma client
WORKDIR ${LAMBDA_TASK_ROOT}/prisma
RUN python -m prisma generate && \
    chmod -R 755 ${LAMBDA_TASK_ROOT}/.prisma

# Switch back to Lambda task root
WORKDIR ${LAMBDA_TASK_ROOT}

# Set the handler for AWS Lambda
CMD [ "app.main.handler" ]