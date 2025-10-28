# Project Management Agent - Makefile
# Provides convenient commands for development and testing

.PHONY: help install test test-deerflow test-conversation test-database test-api test-all clean dev build

# Default target
help:
	@echo "Project Management Agent - Available Commands"
	@echo "=============================================="
	@echo ""
	@echo "Development:"
	@echo "  install     - Install all dependencies"
	@echo "  dev         - Start development environment"
	@echo "  build       - Build production images"
	@echo ""
	@echo "Testing:"
	@echo "  test        - Run all tests"
	@echo "  test-deerflow - Run DeerFlow integration tests"
	@echo "  test-conversation - Run conversation flow tests"
	@echo "  test-database - Run database model tests"
	@echo "  test-api    - Run FastAPI endpoint tests"
	@echo ""
	@echo "Utilities:"
	@echo "  clean       - Clean up temporary files"
	@echo "  logs        - View application logs"
	@echo "  status      - Check service status"

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	uv sync
	@echo "✅ Dependencies installed"

# Development environment
dev:
	@echo "🚀 Starting development environment..."
	docker-compose up -d postgres redis
	@echo "⏳ Waiting for services to start..."
	sleep 10
	@echo "🔧 Starting API server..."
	uv run uvicorn api.main:app --reload --port 8000 &
	@echo "🎨 Starting frontend..."
	cd frontend && npm run dev &
	@echo "✅ Development environment started"
	@echo "Frontend: http://localhost:3000"
	@echo "API: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"

# Build production images
build:
	@echo "🏗️ Building production images..."
	docker-compose -f docker-compose.prod.yml build
	@echo "✅ Production images built"

# Run all tests
test: test-all

# Run specific test suites
test-deerflow:
	@echo "🦌 Running DeerFlow tests..."
	python run_tests.py deerflow

test-conversation:
	@echo "💬 Running conversation flow tests..."
	python run_tests.py conversation

test-database:
	@echo "🗄️ Running database tests..."
	python run_tests.py database

test-api:
	@echo "🔌 Running API tests..."
	python run_tests.py api

test-all:
	@echo "🚀 Running all tests..."
	python run_tests.py all

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	docker-compose down -v
	docker system prune -f
	rm -rf frontend/node_modules
	rm -rf frontend/.next
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .coverage
	@echo "✅ Cleanup completed"

# View logs
logs:
	@echo "📋 Viewing application logs..."
	docker-compose logs -f

# Check status
status:
	@echo "📊 Checking service status..."
	docker-compose ps

# Quick start (install + test + dev)
quickstart: install test-all dev
	@echo "🎉 Quick start completed!"

# Production deployment
deploy:
	@echo "🚀 Deploying to production..."
	docker-compose -f docker-compose.prod.yml up -d
	@echo "✅ Production deployment completed"

# Stop all services
stop:
	@echo "🛑 Stopping all services..."
	docker-compose down
	@echo "✅ All services stopped"