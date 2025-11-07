.PHONY: up down logs test seed

up:
docker-compose up -d --build
sleep 3

down:
docker-compose down

logs:
docker-compose logs -f

seed:
docker-compose exec app python -m app.app.db.seed

TEST_APP=cd /app && pytest
TEST_RUNNER=cd /runner && pytest

test:
docker-compose exec app bash -lc "$(TEST_APP)"
docker-compose exec runner bash -lc "$(TEST_RUNNER)"
