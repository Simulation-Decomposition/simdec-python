.PHONY: help prepare doc test serve build publish-production
.DEFAULT_GOAL := help
SHELL:=/bin/bash

ifndef version
   override version = development
endif

ifndef region
   override region = europe-north1
endif

ifndef project
   override project = delta-entity-401706
endif

ifndef PANEL_TOKEN
   # only for local dev, another token is used for deployment
   override PANEL_TOKEN = e41ea4c145bf13a60c8779c24356
endif


# Add help text after each target name starting with '\#\#'
help:   ## show this help
	@echo -e "Help for this makefile\n"
	@echo "Possible commands are:"
	@grep -h "##" $(MAKEFILE_LIST) | grep -v grep | sed -e 's/\(.*\):.*##\(.*\)/    \1: \2/'

prepare:  ## Install dependencies and pre-commit hook
	pip install -e ".[dev]"
	pre-commit install
	gcloud init
	gcloud auth configure-docker europe-north1-docker.pkg.dev

doc:  ## Build Sphinx documentation
	sphinx-build -b html docs docs/html

test:  ## Run tests with coverage
	pytest --cov simdec --cov-report term-missing

serve-dev:  ## Serve Panel dashboard - Dev mode
	panel serve panel/app.py --show --autoreload

serve:  ## Serve Panel dashboard - Prod mode
	PANEL_BASIC_AUTH=$(PANEL_TOKEN) panel serve panel/app.py \
		--cookie-secret panel_cookie_secret \
		--basic-login-template panel/login.html \
		--logout-template panel/logout.html \
		--static-dirs _static=docs/_static

build-local:
	docker build -f ./Dockerfile \
		--build-arg PANEL_TOKEN=$(PANEL_TOKEN) \
		--tag simdec-panel:$(version) \
	    --pull \
	    ./.

run-local: build-local
	docker run --rm -it \
    --name=simdec-panel \
	--memory=1g \
	--cpuset-cpus=0 \
	-e ENV=development \
	-p "8080:8080" \
	simdec-panel:$(version)

build:
	docker build -f ./Dockerfile \
		--platform linux/amd64 \
		--build-arg PANEL_TOKEN=$(PANEL_TOKEN) \
		--tag simdec-panel:$(version) \
	    --pull \
	    ./.

run: build
	docker run --rm -it \
    --name=simdec-panel \
	--memory=1g \
	--cpuset-cpus=0 \
	-e ENV=development \
	-p "8080:8080" \
	simdec-panel:$(version)

publish-production: build
	docker tag simdec-panel:$(version) $(region)-docker.pkg.dev/$(project)/simdec-panel/simdec-panel:$(version)
	docker push $(region)-docker.pkg.dev/$(project)/simdec-panel/simdec-panel:$(version)

production: publish-production
	@echo "Deploying '$(version)'."
	gcloud run deploy simdec-panel \
	                  --concurrency=10 \
	                  --max-instances=1 \
	                  --region=$(region) \
	                  --port=8080 \
	                  --set-env-vars ENV=production \
	                  --set-secrets=PANEL_BASIC_AUTH=PANEL_TOKEN:latest \
	                  --allow-unauthenticated \
	                  --timeout=600 \
	                  --service-account simdec-panel@delta-entity-401706.iam.gserviceaccount.com \
	                  --image=$(region)-docker.pkg.dev/$(project)/simdec-panel/simdec-panel:$(version) \
	                  --memory 1Gi
