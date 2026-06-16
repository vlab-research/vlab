# repo-wide targets
#
# Most users should run `make release` which is the safe, GHCR-verifying
# helper behind scripts/release.sh. Long-form flags are passed through.

SERVICE ?=
VERSION ?=

.PHONY: build release tag release-wait check-pulls

build: ## Builds all of the go modules (api + inference)
	$(MAKE) -C api build
	$(MAKE) -C inference build

release: ## Tag, push, watch GH Actions run, verify image (SERVICE=... VERSION=...)
	@if [[ -z "$(SERVICE)" || -z "$(VERSION)" ]]; then \
		echo "usage: make release SERVICE=source-typeform VERSION=v0.1.2"; \
		exit 2; \
	fi
	./scripts/release.sh "$(SERVICE)" "$(VERSION)"

tag: ## Just tag + push, without watching (advanced; avoid; use 'release' instead)
	@if [[ -z "$(SERVICE)" || -z "$(VERSION)" ]]; then \
		echo "usage: make tag SERVICE=source-typeform VERSION=v0.1.2 [SHA=commit]"; \
		exit 2; \
	fi
	git tag -a "$(SERVICE)-$(VERSION)" "${SHA:-HEAD}" \
		-m "Release $(SERVICE) $(VERSION)"
	git push origin "$(SERVICE)-$(VERSION)"

release-wait: ## Poll gh run + GHCR for an already-pushed tag
	@if [[ -z "$(SERVICE)" || -z "$(VERSION)" ]]; then \
		echo "usage: make release-wait SERVICE=source-typeform VERSION=v0.1.2"; \
		exit 2; \
	fi
	./scripts/release.sh --allow-dirty "$(SERVICE)" "$(VERSION)" \
		"$(SERVICE)-$(VERSION)" 2>/dev/null || true

check-pulls: ## Surface any pods stuck in ImagePullBackOff/ErrImagePull > 5m
	./scripts/check-imagepullbackoff.sh
