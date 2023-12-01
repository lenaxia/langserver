# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Set environment variables for runtime
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV FLASK_APP=langserver
ENV FLASK_ENV=production

# Set default values for PUID and PGID
ARG PUID=1000
ARG PGID=1000

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gcc

# Add a non-root user and switch to it
RUN groupadd -r appuser -g ${PGID} && useradd -r -g appuser -u ${PUID} appuser

# Create and set ownership of necessary directories
RUN mkdir -p /home/appuser && chown -R appuser:appuser /home/appuser
RUN chown -R appuser:appuser /app

# Install any needed packages specified in requirements.txt as root
# This ensures global installation
USER root
COPY . .
RUN pip3 install --no-cache-dir -r requirements.txt

# Switch back to non-root user for security
USER appuser

# Copy the current directory contents into the container at /usr/src/app
COPY . .
RUN pip3 show flask

# Make port 80 available to the world outside this container
EXPOSE 80

# Run app.py when the container launches
CMD ["flask", "run", "--host=0.0.0.0", "--port=80"]

