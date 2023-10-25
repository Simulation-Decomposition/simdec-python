.PHONY: help prepare doc test serve build publish-production deploy-production promote-production production
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

# Doc and tests

doc:  ## Build Sphinx documentation
	sphinx-build -b html docs docs/html

test:  ## Run tests with coverage
	pytest --cov simdec --cov-report term-missing

# Dashboard commands

serve-dev:  ## Serve Panel dashboard - Dev mode
	panel serve panel/app.py \
 		--show --autoreload \
 		--static-dirs _static=docs/_static \
 		--reuse-sessions --warm

serve-oauth:  ## Serve Panel dashboard - Prod mode with OAuth2. Needs: PANEL_OAUTH_REDIRECT_URI, PANEL_OAUTH_KEY, PANEL_OAUTH_SECRET, PANEL_OAUTH_ENCRYPTION
	PANEL_OAUTH_SCOPE=email panel serve panel/app.py \
		--show \
		--cookie-secret panel_cookie_secret_oauth \
		--basic-login-template panel/login.html \
		--logout-template panel/logout.html \
		--oauth-provider custom_google \
		--static-dirs _static=docs/_static \
		--reuse-sessions --warm

# Deployment commands
# --progress=plain

build-local:  ## Build for local architecture
	docker build -f ./panel/Dockerfile \
		--tag simdec-panel-local:$(version) \
	    --pull \
	    ./.

run-local: build-local
	docker run --rm -it \
    --name=simdec-panel-local \
	--memory=1g \
	--cpuset-cpus=0 \
	-e ENV=development \
	-e PANEL_OAUTH_SCOPE=email \
	-e PANEL_OAUTH_REDIRECT_URI=$(PANEL_OAUTH_REDIRECT_URI) \
	-e PANEL_OAUTH_SECRET=$(PANEL_OAUTH_SECRET) \
	-e PANEL_OAUTH_KEY=$(PANEL_OAUTH_KEY) \
	-e PANEL_OAUTH_ENCRYPTION=$(PANEL_OAUTH_ENCRYPTION) \
	-p "5006:8080" \
	simdec-panel-local:$(version)

# Need to specifically build on linux/amd64 to avoid issues on macOS M platform
build:  ## Build for linux/amd64 (production)
	docker build -f ./panel/Dockerfile \
		--platform linux/amd64 \
		--tag simdec-panel:$(version) \
	    --pull \
	    ./.

run: build
	docker run --rm -it \
    --name=simdec-panel \
	--memory=1g \
	--cpuset-cpus=0 \
	-e ENV=development \
	-e PANEL_OAUTH_SCOPE=email \
	-e PANEL_OAUTH_REDIRECT_URI=$(PANEL_OAUTH_REDIRECT_URI) \
	-e PANEL_OAUTH_SECRET=$(PANEL_OAUTH_SECRET) \
	-e PANEL_OAUTH_KEY=$(PANEL_OAUTH_KEY) \
	-e PANEL_OAUTH_ENCRYPTION=$(PANEL_OAUTH_ENCRYPTION) \
	-p "5006:8080" \
	simdec-panel:$(version)

# Ship

publish-production: build  ## Tag and push to GCP
	docker tag simdec-panel:$(version) $(region)-docker.pkg.dev/$(project)/simdec-panel/simdec-panel:$(version)
	docker push $(region)-docker.pkg.dev/$(project)/simdec-panel/simdec-panel:$(version)


deploy-production: publish-production  ## Deploy new revision to GCP
	@echo "Deploying '$(version)'."
	gcloud run deploy simdec-panel \
					  --cpu=2 \
	                  --concurrency=5 \
	                  --min-instances=0 \
	                  --max-instances=2 \
	                  --region=$(region) \
	                  --port=8080 \
	                  --set-env-vars ENV=production \
	                  --set-env-vars PANEL_OAUTH_SCOPE=email \
	                  --set-secrets=PANEL_OAUTH_REDIRECT_URI=PANEL_OAUTH_REDIRECT_URI:latest \
	                  --set-secrets=PANEL_OAUTH_KEY=PANEL_OAUTH_KEY:latest \
	                  --set-secrets=PANEL_OAUTH_SECRET=PANEL_OAUTH_SECRET:latest \
	                  --set-secrets=PANEL_OAUTH_ENCRYPTION=PANEL_OAUTH_ENCRYPTION:latest \
	                  --allow-unauthenticated \
	                  --session-affinity \
	                  --timeout=60m \
	                  --service-account simdec-panel@delta-entity-401706.iam.gserviceaccount.com \
	                  --image=$(region)-docker.pkg.dev/$(project)/simdec-panel/simdec-panel:$(version) \
	                  --memory 2Gi \
	                  --no-traffic

promote-production:  ## Serve new revision to GCP
	gcloud run services update-traffic simdec-panel --to-latest

cloudbuild-production:  ## Build, Deploy and Serve new revision to GCP using cloudbuild
	gcloud builds submit --config panel/cloudbuild.yaml --substitutions COMMIT_SHA=$(git rev-list --max-count=1 HEAD) .
