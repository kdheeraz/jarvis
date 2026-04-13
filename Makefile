.PHONY: dev dev-ollama build up down migrate logs clean

# Development with ChromaDB
dev:
	docker compose -f docker-compose.yaml -f docker-compose.dev.yaml --profile chromadb up --build

# Development with ChromaDB + Ollama
dev-ollama:
	docker compose -f docker-compose.yaml -f docker-compose.dev.yaml --profile chromadb --profile ollama up --build

# Production build
build:
	docker compose build

# Production up (default: chromadb)
up:
	docker compose --profile chromadb up -d

# Stop all services
down:
	docker compose --profile chromadb --profile ollama --profile opensearch --profile pgvector down

# Run database migrations
migrate:
	docker compose exec backend alembic upgrade head

# View logs
logs:
	docker compose logs -f

# Clean volumes
clean:
	docker compose --profile chromadb --profile ollama --profile opensearch --profile pgvector down -v
