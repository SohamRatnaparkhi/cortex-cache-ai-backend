# Use an official Python runtime as a parent image
FROM python:3.10.0-slim


# Set the working directory inside the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port FastAPI will run on
EXPOSE 80

# RUN prisma generate
RUN pip install prisma

RUN prisma generate  

# Run FastAPI using uvicorn as the command
CMD [ "fastapi", "run", "app/main.py", "--port=80", "--workers", "4"]