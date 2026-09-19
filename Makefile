.DEFAULT_GOAL := help

#########################################
# VARIABLES
#########################################
UV ?= uv
RUN ?= $(UV) run
PYTHON ?= $(RUN) python

PACKAGE ?= inferapi

OUT_DIR ?= out
DATA_DIR ?= data
CSV_FILE ?= $(DATA_DIR)/dataset.csv
DATA_FILE ?= $(DATA_DIR)/dataset.parquet
MODEL_FILE ?= $(OUT_DIR)/models/model.joblib
ENV_FILE ?= .env

BIND_ADDR ?= 127.0.0.1
PORT ?= 8000

# TODO(LAB): Write your project ID here below and export the command
#   export GCP_PROJECT= tp2-group-u
GCP_PROJECT ?= tp2-group-u
GCP_REGION ?= northamerica-northeast1
GCP_ZONE ?= $(GCP_REGION)-b
AR_REPO ?= ml520
VM_NAME ?= ml520-vm
VM_USER ?= mlops
VM_DIR ?= /opt/inferapi

IMAGE_NAME ?= inferapi
IMAGE_TAG ?= 0.2.0
AR_IMAGE ?= $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT)/$(AR_REPO)/$(IMAGE_NAME)

#########################################
# DEPENDENCIES
#########################################
.PHONY: install req-install

install: req-install  ## Alias for req-install

req-install:  ## Create/refresh .venv exactly from uv.lock (project installed editable)
	$(UV) sync

#########################################
# SECRETS
#########################################
.PHONY: secrets-show

# Your .env is a copy of .env.example with a real token in it - see the file itself.
secrets-show:  ## Print the local API token (for curl), never the whole file
	@grep '^ML520_SECURITY__API_TOKEN=' $(ENV_FILE) | cut -d= -f2

#########################################
# CODE QUALITY
#########################################
.PHONY: code-quality code-lint code-lint-fix code-format code-format-fix code-format-preview

code-quality:  ## Run lint and format checks, this is what will be graded
	@$(MAKE) --keep-going --no-print-directory code-lint code-format

code-lint:  ## Run lint checks
	$(RUN) ruff check

code-lint-fix:  ## Fix lint errors
	$(RUN) ruff check --fix

code-format:  ## Check code style adherence
	$(RUN) ruff format --check

code-format-fix:  ## Fix code style adherence
	$(RUN) ruff format

code-format-preview:  ## Preview the changes code-format-fix would make
	$(RUN) ruff format --check --diff

#########################################
# TESTS
#########################################
.PHONY: tests

tests:  ## Run the test suite
	$(RUN) pytest

#########################################
# DATA AND MODELS
#########################################
.PHONY: data-convert model-train runs-parallel

data-convert:  ## Rebuild the parquet from the CSV, whether or not it already exists
	$(RUN) $(PACKAGE) data-convert --csv $(CSV_FILE) --parquet $(DATA_FILE)

model-train: ## Train the model, write the artifact to out/models/model.joblib
	$(RUN) $(PACKAGE) train --data $(DATA_FILE) --output $(MODEL_FILE) --overwrite

runs-parallel:  ## Train one model per hyperparameter combination, several at a time
	./scripts/parallel_runs.sh

#########################################
# SERVING
#########################################
.PHONY: serve serve-dev serve-debug serve-entrypoint

serve:  ## Serve the inferapi app
	$(RUN) gunicorn --workers 2 --worker-class uvicorn.workers.UvicornWorker \
		--bind $(BIND_ADDR):$(PORT) $(PACKAGE).serve:app

serve-dev:  ## DEV server for inferapi app with hot reload
	$(RUN) uvicorn $(PACKAGE).serve:app --reload --port $(PORT) --host $(BIND_ADDR)

# Waits for your editor to attach on port 5678 before importing anything, which is
# the only way to put a breakpoint in create_app() and have it hit.
serve-debug:  ## Serve under debugpy and wait for the debugger to attach (port 5678)
	$(PYTHON) -m debugpy --listen 5678 --wait-for-client \
		-m uvicorn $(PACKAGE).serve:app --port $(PORT) --host $(BIND_ADDR)

serve-entrypoint:  ## Start the service the way systemd and the container do
	set -a; . ./$(ENV_FILE); set +a; ./scripts/entrypoint.sh

#########################################
# GCP AND THE VM
#########################################
.PHONY: check-project check-ssh-config gcp-bootstrap vm-create vm-ssh-config vm-setup vm-sync vm-ssh vm-forward vm-stop vm-start vm-delete

#
# NOTE(LAB): `gcloud compute config-ssh` writes an entry into your ~/.ssh/config.
#			  Use that host to connect to the VM
VM_HOST ?= $(VM_NAME).$(GCP_ZONE).$(GCP_PROJECT)
SSH_TARGET ?= $(VM_USER)@$(VM_HOST)

check-project:
	@test -n "$(GCP_PROJECT)" || { echo "set it first: export GCP_PROJECT=<your-project-id>"; exit 1; }

check-ssh-config: check-project
	@grep -q '$(VM_HOST)' ~/.ssh/config 2>/dev/null \
		|| { echo "no ssh config entry for $(VM_HOST): run 'make vm-ssh-config' first"; exit 1; }

gcp-bootstrap: check-project  ## One-time GCP setup: APIs, image repository, VM identity, firewall
	./scripts/gcp_bootstrap.sh $(GCP_PROJECT)

vm-create: check-project  ## Create the Compute Engine VM
	gcloud compute instances create $(VM_NAME) \
		--project=$(GCP_PROJECT) \
		--zone=$(GCP_ZONE) \
		--machine-type=e2-standard-2 \
		--image-family=ubuntu-2404-lts-amd64 \
		--image-project=ubuntu-os-cloud \
		--boot-disk-size=30GB \
		--service-account=ml520-vm@$(GCP_PROJECT).iam.gserviceaccount.com \
		--scopes=https://www.googleapis.com/auth/cloud-platform \
		--metadata=enable-oslogin=FALSE

# NOTE(LAB): The external address is ephemeral: it changes every time the VM stops and starts
vm-ssh-config: check-project  ## Create the mlops user and teach your ssh client about the VM
	gcloud compute ssh $(VM_USER)@$(VM_NAME) \
		--project=$(GCP_PROJECT) --zone=$(GCP_ZONE) --command=true
	gcloud compute config-ssh --project=$(GCP_PROJECT)
	@echo "you can now: ssh $(SSH_TARGET)"

vm-setup: check-ssh-config  ## Launch the setup script to install docker, uv, rsync, screen and make on the VM, and create /opt/inferapi
	@echo "Copying vm setup script"
	scp scripts/vm_setup.sh $(SSH_TARGET):~/
	@echo "Executing vm setup script via SSH"
	ssh $(SSH_TARGET) 'bash ~/vm_setup.sh'


vm-sync: check-ssh-config  ## Copy the project to /opt/inferapi on the VM
	VM_DIR=$(VM_DIR) ./scripts/vm_sync.sh $(SSH_TARGET)


vm-ssh: check-ssh-config  ## Open a shell on the VM
	ssh $(SSH_TARGET)

vm-forward: check-ssh-config  ## Create an SSH tunnel to reach the VM's service at http://localhost:8000
	ssh -N -L $(PORT):localhost:8000 $(SSH_TARGET)

vm-stop: check-project  ## Stop the VM, keeping the disk. Do this whenever you stop working
	gcloud compute instances stop $(VM_NAME) --project=$(GCP_PROJECT) --zone=$(GCP_ZONE)

vm-start: check-project  ## Start the VM again and refresh the ssh config with its new address
	gcloud compute instances start $(VM_NAME) --project=$(GCP_PROJECT) --zone=$(GCP_ZONE)
	@$(MAKE) --no-print-directory vm-ssh-config

vm-delete: check-project  ## Delete the VM. Nothing after TP2 uses it
	gcloud compute instances delete $(VM_NAME) --project=$(GCP_PROJECT) --zone=$(GCP_ZONE)

#########################################
# CONTAINERS
#########################################
.PHONY: docker-context docker-build docker-run docker-push compose-up compose-down compose-logs

docker-context:  ## Show the content of the build context
	@printf 'FROM scratch\nCOPY . /' | DOCKER_BUILDKIT=1 docker build -f- -o- . | tar -tv

# NOTE(LAB): We pass --platform because the VM is amd64. Without the flag, an image built on an Apple Silicon laptop (arm64) and fails to launch VM with `exec format error`.
docker-build:  ## Build the image for linux/amd64
	docker build --platform linux/amd64 -t $(IMAGE_NAME):$(IMAGE_TAG) .

docker-run:  ## Run the image locally on port 8000
	docker run --rm -p $(PORT):8000 \
		-e ML520_SECURITY__API_TOKEN=$$($(MAKE) --no-print-directory secrets-show) \
		$(IMAGE_NAME):$(IMAGE_TAG)

docker-push: check-project  ## Tag and push the image to Artifact Registry
	docker tag $(IMAGE_NAME):$(IMAGE_TAG) $(AR_IMAGE):$(IMAGE_TAG)
	docker push $(AR_IMAGE):$(IMAGE_TAG)
	@echo "pushed $(AR_IMAGE):$(IMAGE_TAG)"

compose-up:  ## Build and start the service plus the load generator
	docker compose up --build

compose-down:  ## Stop the stack and remove its containers
	docker compose down

compose-logs:  ## Save the service's container logs to out/logs/compose_app.log
	@mkdir -p $(OUT_DIR)/logs
	docker compose logs --no-log-prefix inferapi > $(OUT_DIR)/logs/compose_app.log
	@echo "wrote $(OUT_DIR)/logs/compose_app.log"

#########################################
# NOTEBOOKS
#########################################
.PHONY: notebook-launch

notebook-launch:  ## Launch JupyterLab (pulls in the `notebooks` dependency group)
	$(UV) run --group notebooks jupyter lab --no-browser

#########################################
# LAB
#########################################
.PHONY: submit

submit:  ## Bundle the full history for hand-in: make submit TEAM=<number>
	@test -n "$(TEAM)" || { echo "usage: make submit TEAM=<number>"; exit 1; }
	@mkdir -p $(OUT_DIR)
	git bundle create $(OUT_DIR)/tp2_team_$(TEAM).bundle --all
	@echo "wrote $(OUT_DIR)/tp2_team_$(TEAM).bundle"

#########################################
# HOUSEKEEPING
#########################################
.PHONY: help

# Taken from: https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
help:  ## Show this help
	@grep -h -E '^[0-9a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

-include Makefile.teacher
