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
	panel serve panel/app.py \
 		--show --autoreload \
 		--static-dirs _static=docs/_static \
 		--reuse-sessions --warm

serve:  ## Serve Panel dashboard - Prod mode with basic auth
	panel serve panel/app.py \
		--show \
		--cookie-secret panel_cookie_secret_oauth \
		--basic-login-template panel/login.html \
		--logout-template panel/logout.html \
		--static-dirs _static=docs/_static \
		--reuse-sessions --warm

serve-oauth:  ## Serve Panel dashboard - Prod mode with OAuth2
	panel serve panel/app.py \
		--show \
		--cookie-secret panel_cookie_secret_oauth \
		--logout-template panel/logout.html \
		--oauth-provider google \
		--static-dirs _static=docs/_static \
		--reuse-sessions --warm

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
					  --cpu=2 \
	                  --concurrency=5 \
	                  --min-instances=0 \
	                  --max-instances=2 \
	                  --region=$(region) \
	                  --port=8080 \
	                  --set-env-vars ENV=production \
	                  --set-secrets=PANEL_OAUTH_REDIRECT_URI=PANEL_OAUTH_REDIRECT_URI:latest \
	                  --set-secrets=PANEL_OAUTH_KEY=PANEL_OAUTH_KEY:latest \
	                  --set-secrets=PANEL_OAUTH_SECRET=PANEL_OAUTH_SECRET:latest \
	                  --allow-unauthenticated \
	                  --session-affinity \
	                  --timeout=60m \
	                  --service-account simdec-panel@delta-entity-401706.iam.gserviceaccount.com \
	                  --image=$(region)-docker.pkg.dev/$(project)/simdec-panel/simdec-panel:$(version) \
	                  --memory 2Gi
