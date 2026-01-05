SHELL := /bin/bash
PYTHON ?= python
PIP ?= pip

PROPOSAL_ID ?= demo
AGENT ?= agent
GOAL ?= demo goal
SCOPE ?= services/payment/
CONSTRAINTS ?= no_production_push_by_agent
EVIDENCE ?= aap/evidence/example/results.json
BY ?= you@example.com
REASON ?= ok
LIMIT ?= 20

.PHONY: deps-base deps-api deps-dev propose evaluate decide list show audit api hook totp commit test

deps-base:
	@$(PIP) install -e .

deps-api:
	@$(PIP) install -e .[api]

deps-dev:
	@$(PIP) install -e .[dev]

propose:
	$(PYTHON) -m aap.cli propose --agent "$(AGENT)" --goal "$(GOAL)" --scope $(SCOPE) --constraints $(CONSTRAINTS) --id $(PROPOSAL_ID)

evaluate:
	$(PYTHON) -m aap.cli evaluate $(PROPOSAL_ID) --evidence $(EVIDENCE)

decide:
	@if [ -z "$(OTP)" ]; then echo "OTP is required (set OTP=<code>)"; exit 1; fi
	$(PYTHON) -m aap.cli decide $(PROPOSAL_ID) --accept --by $(BY) --reason "$(REASON)" --otp $(OTP)

commit:
	$(PYTHON) -m aap.cli commit $(PROPOSAL_ID) --stage-all

list:
	$(PYTHON) -m aap.cli list

show:
	$(PYTHON) -m aap.cli show $(PROPOSAL_ID)

audit:
	$(PYTHON) -m aap.cli audit --limit $(LIMIT)

api:
	@if [ -z "$$AAP_API_TOKEN" ]; then echo "Set AAP_API_TOKEN (or add to aap/api_tokens.txt) before running the API"; exit 1; fi
	AAP_API_TOKEN="$$AAP_API_TOKEN" uvicorn aap.api:app --reload

hook:
	@if [ ! -d .git ]; then echo "Not a git repo; init or run from repo root"; exit 1; fi
	ln -sf ../../aap/hooks/pre-receive .git/hooks/pre-receive
	@echo "Pre-receive hook installed"

totp:
	$(PYTHON) - <<'PY'\nfrom aap.auth import totp_now\nprint(totp_now())\nPY

test:
	$(PYTHON) -m pytest
