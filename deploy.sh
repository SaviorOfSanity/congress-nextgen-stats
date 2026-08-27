#!/usr/bin/env bash
set -e

echo "=== Pulling Latest Changes from Git ==="
git pull origin main

echo "=== Rebuilding & Restarting Docker Containers ==="
docker compose down
docker compose up -d --build

echo "=== Deployment Complete! ==="
echo "Application running at: http://$(hostname -I | awk '{print $1}'):8000"
