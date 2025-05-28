#!/bin/bash

# Exit on error
set -e

# Default values
IMAGE_NAME="alice-is-missing"
VERSION="latest"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1"
            exit 1
            ;;
    esac
done

echo "Building Docker image ${IMAGE_NAME}:${VERSION}..."

# Build the image
docker build -t "${IMAGE_NAME}:${VERSION}" .

# Tag as latest if version is not "latest"
if [ "$VERSION" != "latest" ]; then
    docker tag "${IMAGE_NAME}:${VERSION}" "${IMAGE_NAME}:latest"
fi

echo "Build completed successfully!"

