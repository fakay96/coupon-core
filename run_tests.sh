#!/bin/bash

# Stop any existing containers
docker-compose -f docker-compose.test.yaml down

# Start test services
docker-compose -f docker-compose.test.yaml up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Run migrations
python manage.py migrate --settings=coupon_core.settings.test

# Run tests with coverage
pytest --cov=. --cov-report=xml --cov-report=term-missing

# Stop test services
docker-compose -f docker-compose.test.yaml down 