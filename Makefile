.PHONY: version version-noninteractive test test-unit test-lint test-format test-container test-container-verbose test-fixtures test-fixtures-container test-fixture-local demo-file download-yamnet-model update-yamnet-model help

help:
	@echo "Available targets:"
	@echo "  make test-container       Build and smoke-test the container image"
	@echo "  make test-container-verbose  Build and smoke-test with more runtime logs"
	@echo "  make test-fixtures        Run the fixture manifest and file checks"
	@echo "  make test-fixtures-container  Run the dog/train fixtures through the container with local logging"
	@echo "  make demo-file FILE=path/to/file.wav  Run the demo formatter against one audio file"
	@echo "  make download-yamnet-model  Download the official YAMNet class map"
	@echo "  make update-yamnet-model  Download the Kaggle YAMNet TFLite package and stage the assets"

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

download-yamnet-model:
	@mkdir -p models
	@curl -L --fail -o models/yamnet_class_map.csv https://raw.githubusercontent.com/tensorflow/models/master/research/audioset/yamnet/yamnet_class_map.csv
	@echo "Downloaded the official YAMNet class map to models/yamnet_class_map.csv"
	@echo "The TFLite model is still fetched by the update target."

update-yamnet-model:
	@mkdir -p models/tmp-yamnet
	@rm -f models/tmp-yamnet/model.tar.gz
	@curl -L --fail -o models/tmp-yamnet/model.tar.gz https://www.kaggle.com/api/v1/models/google/yamnet/tfLite/classification-tflite/1/download
	@tar -xzf models/tmp-yamnet/model.tar.gz -C models/tmp-yamnet
	@find models/tmp-yamnet -type f \( -name '*.tflite' -o -name '*.tft' -o -name 'yamnet_label_list.txt' -o -name '*.txt' \) | sort | while read file; do \
		case "$$file" in \
			*"1.tflite"*) cp "$$file" models/yamnet.tflite ;; \
			*"yamnet_label_list.txt"*) cp "$$file" models/yamnet_class_map.csv ;; \
			*"class_map"*|*"class"*"map"*) cp "$$file" models/yamnet_class_map.csv ;; \
			*.txt) cp "$$file" models/yamnet_labels.txt ;; \
		esac; \
	done
	@rm -rf models/tmp-yamnet
	@echo "Staged updated YAMNet model assets in models/"
	@echo "Files present:"
	@ls -1 models | grep -E 'yamnet' || true

test-fixtures:
	@. .venv/bin/activate && pytest -q tests/test_audio_fixtures.py tests/test_audio_classifier_integration.py

demo-file:
	@. .venv/bin/activate && export PYTHONPATH="$$(pwd)/ha-audio-events" && python -m app.demo "$(FILE)"

test-fixture-local:
	@mkdir -p /tmp/ha-audio-events-fixture
	@printf 'model: yamnet\nbuffer_seconds: 3.0\naudio:\n  sample_rate: 16000\n  channels: 1\n  format: pcm_s16le\n  source_path: /tmp/fixture.wav\nactivity:\n  rms_threshold: 0.001\n  peak_threshold: 0.001\n  hold_time: 0.5\nclassifier:\n  threshold: 0.01\n  max_results: 5\n  include: []\n  exclude: []\naggregation:\n  start_confidence: 0.01\n  end_timeout: 1.0\nhomeassistant:\n  enabled: false\nmqtt:\n  enabled: false\n' > /tmp/ha-audio-events-fixture-config.yaml
	@python -c "from pathlib import Path; import subprocess; fixture=Path('tests/fixtures/audio/train/freesound_community-8-freight-train_126s.mp3'); output=Path('/tmp/ha-audio-events-fixture/fixture.wav'); subprocess.run(['ffmpeg','-y','-i',str(fixture),'-ar','16000','-ac','1','-f','wav',str(output)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); print(f'Converted {fixture.name} -> {output.name}')"
	@. .venv/bin/activate && export PYTHONPATH="$$(pwd)/ha-audio-events" && cp /tmp/ha-audio-events-fixture-config.yaml config.yaml && python -m app.demo /tmp/ha-audio-events-fixture/fixture.wav

test-container:
	@echo "Building container image..."
	@podman build -t ha-audio-events-test ./ha-audio-events
	@.venv/bin/python -c "import math,wave; from pathlib import Path; p=Path('test_audio.wav'); w=wave.open(str(p),'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); [w.writeframesraw((int(12000*math.sin(2*math.pi*440*i/16000)) if i % 800 < 400 else 0).to_bytes(2,'little',signed=True)) for i in range(16000)]; w.close()"
	@printf 'model: yamnet\nbuffer_seconds: 3.0\naudio:\n  sample_rate: 16000\n  channels: 1\n  format: pcm_s16le\n  source_path: /tmp/test_audio.wav\nactivity:\n  rms_threshold: 0.01\n  peak_threshold: 0.01\n  hold_time: 0.1\nclassifier:\n  threshold: 0.1\n  max_results: 5\n  include:\n    - speech\n    - dog\n    - train\n    - thunder\n    - siren\n  exclude:\n    - music\n    - silence\nhomeassistant:\n  enabled: false\nmqtt:\n  enabled: false\nwebui:\n  enabled: false\n' > /tmp/ha-audio-events-test-config.yaml
	@echo "Running container smoke test..."
	@podman run --rm \
		-e PYTHONUNBUFFERED=1 \
		-v "$$(pwd):/data:Z" \
		-v /tmp/ha-audio-events-test-config.yaml:/tmp/config.yaml:Z \
		localhost/ha-audio-events-test \
		timeout 30 \
		bash -c 'set -e; cd /app && cp /data/test_audio.wav /tmp/test_audio.wav && cp /tmp/config.yaml /app/config.yaml && python3 -m app.main'

test-fixtures-container:
	@echo "Building container image..."
	@podman build -t ha-audio-events-test ./ha-audio-events
	@mkdir -p /tmp/ha-audio-events-fixtures
	@printf 'model: yamnet\nbuffer_seconds: 3.0\naudio:\n  sample_rate: 16000\n  channels: 1\n  format: pcm_s16le\n  source_path: /tmp/fixture.wav\nactivity:\n  rms_threshold: 0.03\n  peak_threshold: 0.05\n  hold_time: 0.5\nclassifier:\n  threshold: 0.1\n  max_results: 5\n  include:\n    - speech\n    - dog\n    - train\n    - thunder\n    - siren\n  exclude:\n    - music\n    - silence\nhomeassistant:\n  enabled: false\nmqtt:\n  enabled: false\nwebui:\n  enabled: false\n' > /tmp/ha-audio-events-fixture-config.yaml
	@for fixture in tests/fixtures/audio/train/freesound_community-8-freight-train_126s.mp3 tests/fixtures/audio/dog-barking/audiopapkin-barking-large-and-small-dog-290711.mp3; do \
		cp "$$fixture" /tmp/ha-audio-events-fixtures/fixture.mp3; \
		.venv/bin/python -c "from pathlib import Path; import subprocess; fixture=Path('/tmp/ha-audio-events-fixtures/fixture.mp3'); output=Path('/tmp/ha-audio-events-fixtures/fixture.wav'); subprocess.run(['ffmpeg','-y','-i',str(fixture),'-ar','16000','-ac','1','-f','wav',str(output)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); print(f'Converted {fixture.name} -> {output.name}')"; \
		podman run --rm -i -e PYTHONUNBUFFERED=1 -v "$$(pwd):/data:Z" -v /tmp/ha-audio-events-fixture-config.yaml:/tmp/config.yaml:Z -v /tmp/ha-audio-events-fixtures:/tmp/fixtures:Z localhost/ha-audio-events-test timeout 60 /bin/bash -lc 'cd /app && cp /tmp/fixtures/fixture.wav /tmp/fixture.wav && cp /tmp/config.yaml /app/config.yaml && /app/run.sh' ; \
	done

test-container-verbose:
	@echo "Building container image with verbose logging..."
	@podman build -t ha-audio-events-test ./ha-audio-events
	@.venv/bin/python -c "import math,wave; from pathlib import Path; p=Path('test_audio.wav'); w=wave.open(str(p),'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); [w.writeframesraw((int(12000*math.sin(2*math.pi*440*i/16000)) if i % 800 < 400 else 0).to_bytes(2,'little',signed=True)) for i in range(16000)]; w.close()"
	@printf 'model: yamnet\nbuffer_seconds: 3.0\naudio:\n  sample_rate: 16000\n  channels: 1\n  format: pcm_s16le\n  source_path: /tmp/test_audio.wav\nactivity:\n  rms_threshold: 0.01\n  peak_threshold: 0.01\n  hold_time: 0.1\nclassifier:\n  threshold: 0.1\n  max_results: 5\n  include:\n    - speech\n    - dog\n    - train\n    - thunder\n    - siren\n  exclude:\n    - music\n    - silence\nhomeassistant:\n  enabled: false\nmqtt:\n  enabled: false\nwebui:\n  enabled: false\n' > /tmp/ha-audio-events-test-config.yaml
	@podman run --rm -i -e PYTHONUNBUFFERED=1 -v "$$(pwd):/data:Z" -v /tmp/ha-audio-events-test-config.yaml:/tmp/config.yaml:Z localhost/ha-audio-events-test timeout 60 /bin/bash -lc 'cd /app && cp /data/test_audio.wav /tmp/test_audio.wav && cp /tmp/config.yaml /app/config.yaml && /app/run.sh'

test: test-lint test-format test-with-coverage

test-unit:
	@.venv/bin/activate && PYTHONPATH=ha-audio-events .venv/bin/pytest -v

test-lint:
	@.venv/bin/activate && PYTHONPATH=ha-audio-events .venv/bin/ruff check ha-audio-events/app/ tests/

test-format:
	@.venv/bin/activate && PYTHONPATH=ha-audio-events .venv/bin/black --target-version=py312 ha-audio-events/app/ tests/

test-with-coverage:
	@.venv/bin/activate && PYTHONPATH=ha-audio-events .venv/bin/pytest --cov=ha-audio-events/app --cov-fail-under=80 --cov-report=term-missing -v