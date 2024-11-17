# Use AWS Lambda Python 3.10 base image
FROM public.ecr.aws/lambda/python:3.10

# Install Node.js 16 and npm
RUN yum -y update && \
    curl -sL https://rpm.nodesource.com/setup_16.x | bash - && \
    yum install -y nodejs && \
    yum clean all

# Verify installation of node and npm
RUN node -v && npm -v

# Create directories for Prisma and the FastAPI app
RUN mkdir -p ${LAMBDA_TASK_ROOT}/prisma
RUN mkdir -p ${LAMBDA_TASK_ROOT}/app
# Copy Python requirements and Prisma files
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
COPY prisma/ ${LAMBDA_TASK_ROOT}/prisma/

# Install Python dependencies
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Install Prisma and generate Python Prisma client
# RUN npm install -g prisma
RUN cd ${LAMBDA_TASK_ROOT} && prisma generate

# Copy FastAPI application files
COPY app/ ${LAMBDA_TASK_ROOT}/app/

# Set the handler for AWS Lambda
CMD [ "app.main.handler" ]