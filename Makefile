.PHONY: version version-noninteractive help

help:
	@echo "Available targets:"
	@echo "  make version              Prompt for a new version and confirm it"
	@echo "  make version VERSION=0.2.0  Non-interactive version bump"
	@echo "  make version-noninteractive VERSION=0.2.0"

version:
	@current_version=$$(grep -E '^version\s*=\s*"' pyproject.toml | head -n1 | sed -E 's/.*"([^"]+)"/\1/'); \
	echo "Current version: $$current_version"; \
	if [ -n "$(VERSION)" ]; then \
		target_version="$(VERSION)"; \
		echo "Using version from make variable: $$target_version"; \
	else \
		read -p "Enter new version: " target_version; \
	fi; \
	if [ -z "$$target_version" ]; then \
		echo "Version is required"; \
		exit 1; \
	fi; \
	if [ -z "$(VERSION)" ]; then \
		read -p "Confirm version $$target_version? [y/N] " confirm; \
		case "$$confirm" in \
			[Yy]|[Yy][Ee][Ss]) ;; \
			*) echo "Cancelled"; exit 1 ;; \
		esac; \
	fi; \
	PYTHONPATH=ha-audio-events . .venv/bin/activate && python -m app.versioning "$$target_version"

version-noninteractive:
	@current_version=$$(grep -E '^version\s*=\s*"' pyproject.toml | head -n1 | sed -E 's/.*"([^"]+)"/\1/'); \
	echo "Current version: $$current_version"; \
	if [ -z "$(VERSION)" ]; then \
		echo "Usage: make version-noninteractive VERSION=0.2.0"; \
		exit 1; \
	fi; \
	PYTHONPATH=ha-audio-events . .venv/bin/activate && python -m app.versioning "$(VERSION)"
