"""
Web UI server for HA Audio Events add-on.
Provides ingress panel for selecting audio source from Home Assistant entities.
"""

from __future__ import annotations

import asyncio
import logging

from aiohttp import web

from app.addon_mgr import AddonManager
from app.homeassistant.client import HomeAssistantClient

_LOGGER = logging.getLogger(__name__)


class WebUI:
    def __init__(
        self, hass_client: HomeAssistantClient, addon_manager: AddonManager
    ) -> None:
        self.hass_client = hass_client
        self.addon_manager = addon_manager
        self.app = web.Application()
        self.app.router.add_get("/", self.serve_index)
        self.app.router.add_get("/api/cameras", self.get_cameras)
        self.app.router.add_post("/api/source", self.set_source)
        self.app.router.add_get("/api/source", self.get_source)

    async def start(self) -> asyncio.Task:
        """Start the aiohttp web server and return the task."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, "", 8099)
        _LOGGER.info("Web UI server starting on port 8099")
        await site.start()
        _LOGGER.info("Web UI server started successfully")
        return asyncio.create_task(self._keep_server_alive(runner))

    async def _keep_server_alive(self, runner: web.AppRunner) -> None:
        """Keep the server running until cancelled."""
        try:
            # Wait forever until cancelled
            await asyncio.Future()
        except asyncio.CancelledError:
            _LOGGER.info("Web UI server shutting down")
            await runner.cleanup()

    async def serve_index(self, request: web.Request) -> web.Response:
        """Serve the main HTML page for the Web UI."""
        html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HA Audio Events - Source Picker</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: 600;
            color: #555;
        }
        select, input[type="text"] {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
            box-sizing: border-box;
        }
        button {
            background: #007bff;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            transition: background-color 0.2s;
        }
        button:hover {
            background: #0056b3;
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .message {
            padding: 12px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
        .success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .loading {
            text-align: center;
            padding: 20px;
            color: #666;
        }
        .status {
            padding: 10px;
            border-radius: 4px;
            margin-top: 10px;
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>���🎵 HA Audio Events</h1>
        <p class="subtitle">Configure your audio source from Home Assistant entities</p>

        <div id="message-container"></div>

        <form id="source-form">
            <div class="form-group">
                <label for="source-select">Audio Source</label>
                <select id="source-select">
                    <option value="">Loading cameras...</option>
                </select>
            </div>

            <div class="form-group">
                <label for="custom-source">Or enter custom RTSP/URL</label>
                <input 
                    type="text" 
                    id="custom-source" 
                    placeholder="rtsp://192.168.1.100/stream or http://..."
                    style="display: none;"
                >
            </div>

            <div class="form-group">
                <label>Current Source Path</label>
                <div id="current-source" style="padding: 10px; background: #f8f9fa; border-radius: 4px; min-height: 20px;">
                    Loading...
                </div>
            </div>

            <button type="submit" id="submit-btn" disabled>Apply Source</button>
        </form>

        <div id="status" class="status"></div>
    </div>

    <script>
        let cameras = [];
        let currentSource = '';
        let isLoading = true;

        // Load initial data
        async function loadData() {
            try {
                // Load cameras
                const camerasResponse = await fetch('/api/cameras');
                if (camerasResponse.ok) {
                    cameras = await camerasResponse.json();
                } else {
                    throw new Error('Failed to load cameras');
                }

                // Load current source
                const sourceResponse = await fetch('/api/source');
                if (sourceResponse.ok) {
                    const data = await sourceResponse.json();
                    currentSource = data.source || '';
                }

                populateCameraSelect();
                updateCurrentSourceDisplay();
                isLoading = false;
                updateSubmitButton();
            } catch (error) {
                showMessage(`Error loading data: ${error.message}`, 'error');
                isLoading = false;
                updateSubmitButton();
            }
        }

        function populateCameraSelect() {
            const select = document.getElementById('source-select');
            select.innerHTML = '';

            if (cameras.length === 0) {
                select.innerHTML = '<option value="">No cameras found</option>';
                return;
            }

            // Add cameras from HA
            cameras.forEach(camera => {
                const option = document.createElement('option');
                option.value = camera.entity_id;
                option.textContent = `${camera.friendly_name} (${camera.entity_id})`;
                select.appendChild(option);
            });

            // Add custom URL option
            const customOption = document.createElement('option');
            customOption.value = '__custom__';
            customOption.textContent = '--- Enter custom RTSP/URL ---';
            select.appendChild(customOption);
        }

        function updateCurrentSourceDisplay() {
            const display = document.getElementById('current-source');
            if (currentSource) {
                display.textContent = currentSource;
                display.style.color = '#155724';
            } else {
                display.textContent = 'No source configured';
                display.style.color = '#6c757d';
            }
        }

        function updateSubmitButton() {
            const submitBtn = document.getElementById('submit-btn');
            submitBtn.disabled = isLoading;
            submitBtn.textContent = isLoading ? 'Loading...' : 'Apply Source';
        }

        function showMessage(message, type) {
            const container = document.getElementById('message-container');
            const div = document.createElement('div');
            div.className = `message ${type}`;
            div.textContent = message;
            container.innerHTML = '';
            container.appendChild(div);

            // Auto-hide success messages after 5 seconds
            if (type === 'success') {
                setTimeout(() => {
                    if (div.parentNode) {
                        div.parentNode.removeChild(div);
                    }
                }, 5000);
            }
        }

        function showStatus(message, type) {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = `status ${type}`;
            status.style.display = 'block';

            if (type === 'success') {
                setTimeout(() => {
                    status.style.display = 'none';
                }, 10000);
            }
        }

        function getSelectedSource() {
            const select = document.getElementById('source-select');
            const customInput = document.getElementById('custom-source');
            
            if (select.value === '__custom__') {
                return customInput.value.trim();
            }
            return select.value;
        }

        // Toggle custom input visibility
        document.getElementById('source-select').addEventListener('change', function() {
            const customInput = document.getElementById('custom-source');
            if (this.value === '__custom__') {
                customInput.style.display = 'block';
                customInput.required = true;
            } else {
                customInput.style.display = 'none';
                customInput.required = false;
            }
        });

        // Form submission
        document.getElementById('source-form').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const source = getSelectedSource();
            if (!source) {
                showMessage('Please select or enter a source', 'error');
                return;
            }

            const submitBtn = document.getElementById('submit-btn');
            const originalText = submitBtn.textContent;
            submitBtn.disabled = true;
            submitBtn.textContent = 'Applying...';

            try {
                showStatus('Applying audio source configuration...', 'success');
                
                const response = await fetch('/api/source', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ source: source })
                });

                if (response.ok) {
                    const data = await response.json();
                    showMessage('Audio source configured successfully!', 'success');
                    showStatus('Configuration applied. The add-on is restarting to apply changes.', 'success');
                    currentSource = source;
                    updateCurrentSourceDisplay();
                } else {
                    const error = await response.json();
                    showMessage(`Error: ${error.error || 'Failed to configure source'}`, 'error');
                    showStatus(`Error: ${error.error || 'Failed to configure source'}`, 'error');
                }
            } catch (error) {
                showMessage(`Network error: ${error.message}`, 'error');
                showStatus(`Network error: ${error.message}`, 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            }
        });

        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {
            loadData();
        });
    </script>
</body>
</html>
        """
        return web.Response(text=html_content, content_type="text/html")

    async def get_cameras(self, request: web.Request) -> web.Response:
        """Fetch available camera entities from Home Assistant."""
        try:
            state = await self.hass_client.get_state("camera")
            if state is None:
                return web.json_response(
                    {"error": "Failed to fetch camera states"}, status=500
                )

            cameras = []
            for entity in state:
                if isinstance(entity, dict) and entity.get("entity_id", "").startswith(
                    "camera."
                ):
                    cameras.append(
                        {
                            "entity_id": entity["entity_id"],
                            "friendly_name": entity.get(
                                "friendly_name", entity["entity_id"]
                            ),
                        }
                    )

            return web.json_response(cameras)
        except Exception as e:
            _LOGGER.exception("Error fetching cameras")
            return web.json_response({"error": str(e)}, status=500)

    async def get_source(self, request: web.Request) -> web.Response:
        """Get the currently configured source path."""
        try:
            source = await self.addon_manager.get_option("audio", "source_path")
            return web.json_response({"source": source or ""})
        except Exception as e:
            _LOGGER.exception("Error fetching source")
            return web.json_response({"error": str(e)}, status=500)

    async def set_source(self, request: web.Request) -> web.Response:
        """Set the audio source path and restart the add-on."""
        try:
            data = await request.json()
            source = data.get("source")
            if not source:
                return web.json_response(
                    {"error": "Missing source parameter"}, status=400
                )

            success = await self.addon_manager.set_option(
                "audio", "source_path", source
            )
            if not success:
                return web.json_response(
                    {"error": "Failed to set source in add-on options"}, status=500
                )

            restart_success = await self.addon_manager.restart()
            if not restart_success:
                return web.json_response(
                    {"error": "Source configured but failed to restart add-on"},
                    status=500,
                )

            _LOGGER.info("Audio source configured to: %s, add-on restarted", source)
            return web.json_response(
                {
                    "status": "success",
                    "message": "Source configured and add-on restarted",
                }
            )

        except Exception as e:
            _LOGGER.exception("Error setting source")
            return web.json_response({"error": str(e)}, status=500)
