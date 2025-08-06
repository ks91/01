#!/bin/bash

# Script to stop all running Docker containers

echo "Checking for running Docker containers..."

# Get list of running containers
RUNNING_CONTAINERS=$(docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" --no-trunc)

if [ -z "$RUNNING_CONTAINERS" ]; then
    echo "No running Docker containers found."
    exit 0
fi

echo "Running containers:"
echo "$RUNNING_CONTAINERS"
echo ""

# Get IDs of running containers
CONTAINER_IDS=$(docker ps -q)

if [ -n "$CONTAINER_IDS" ]; then
    echo "Stopping all running containers..."
    
    # Stop each container
    for container_id in $CONTAINER_IDS; do
        container_name=$(docker inspect --format='{{.Name}}' $container_id | sed 's/\///')
        echo "Stopping: $container_name ($container_id)"
        docker stop $container_id
    done
    
    echo ""
    echo "All containers have been stopped."
else
    echo "No containers to stop found."
fi 