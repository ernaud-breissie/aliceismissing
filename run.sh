#!/bin/bash

# Exit on error
set -e

# Default values
CONTAINER_NAME="alice-is-missing"
IMAGE_NAME="alice-is-missing"
VERSION="latest"
PORT=80

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1"
            exit 1
            ;;
    esac
done

# Stop and remove existing container if running
if [ "$(docker ps -q -f name=${CONTAINER_NAME})" ]; then
    echo "Stopping existing container..."
    docker stop ${CONTAINER_NAME}
fi

if [ "$(docker ps -aq -f name=${CONTAINER_NAME})" ]; then
    echo "Removing existing container..."
    docker rm ${CONTAINER_NAME}
fi

echo "Starting container ${CONTAINER_NAME}..."

# Run the container
docker run -d \
    --name ${CONTAINER_NAME} \
    -p ${PORT}:80 \
    -v $(pwd)/db.sqlite3:/app/db.sqlite3 \
    -v $(pwd)/media:/app/media \
    -v $(pwd)/static:/app/static \
    --restart unless-stopped \
    ${IMAGE_NAME}:${VERSION}

echo "Container started successfully!"

