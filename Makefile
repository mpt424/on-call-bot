.PHONY: build dist test clean-dockers

WORKSPACE ?= on-call-bot
DOCKER_COMPOSE = docker-compose -p ${WORKSPACE}
DOCKER_COMPOSE_DEV = docker-compose -f docker-compose.yml -f docker-compose.dev.yml -p ${WORKSPACE}

clean:
	git clean -xdf -e .idea -e .vscode -e .cache

test:
	SKIP=hadolint-docker,docker-compose-check pre-commit run --all-files
	python -m pytest

install-precommit: install-requirements
	pre-commit install

build-docker: clean
	$(DOCKER_COMPOSE) build --pull test-svc

test-in-docker: build-docker
	mkdir -p ${HOME}/.cache.tmp/
	$(DOCKER_COMPOSE) down --volumes --remove-orphans
	$(DOCKER_COMPOSE) run --rm test-svc
	$(DOCKER_COMPOSE) down --volumes --remove-orphans

clean-dockers:
	$(DOCKER_COMPOSE) down --volumes --remove-orphans

run-dbs:
	$(DOCKER_COMPOSE_DEV) up -d

retest-in-docker:
	$(DOCKER_COMPOSE) run --rm test-svc

install-requirements:
	poetry install

upgrade-requirements:
	poetry update

validate:
    c

test-custom: clean
	python -m pytest $(filter-out $@,$(MAKECMDGOALS))

test-in-docker-custom:
	$(DOCKER_COMPOSE) run --rm test-svc test-custom $(filter-out $@,$(MAKECMDGOALS))

run-bot:
    docker-compose up -d --build
