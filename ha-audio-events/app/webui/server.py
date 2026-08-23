"""
Web UI server for HA Audio Events add-on.
Provides ingress panel for selecting audio source from Home Assistant entities.
"""

from __future__ import annotations

import asyncio
import csv
import hmac
import logging
import os
from pathlib import Path

from aiohttp import web

from app.addon_mgr import AddonManager
from app.detection.history import EventHistory
from app.homeassistant.client import HomeAssistantClient

_LOGGER = logging.getLogger(__name__)

# Typed application-storage key for the optional shared API token.
# Empty string means "no token configured" (open access / HA ingress).
_AUTH_TOKEN_KEY = web.AppKey("webui_auth_token", str)


@web.middleware
async def auth_middleware(request: web.Request, handler) -> web.StreamResponse:
    """Require a shared token on /api routes when one is configured.

    Behind Home Assistant ingress, requests are already authenticated by the
    Supervisor, so no token is needed. For standalone deployments that expose
    the port directly, set ``webui.auth_token`` to lock the control plane;
    the index page prompts for the token and sends it as ``X-WebUI-Token``.
    """
    expected_token: str = request.app[_AUTH_TOKEN_KEY]
    if expected_token and request.path.startswith("/api/"):
        provided = request.headers.get("X-WebUI-Token")
        if not provided:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                provided = auth_header[len("Bearer ") :]
        if not provided or not hmac.compare_digest(provided, expected_token):
            return web.json_response(
                {"error": "Unauthorized: missing or invalid WebUI token"},
                status=401,
            )
    return await handler(request)


class WebUI:
    def __init__(
        self,
        hass_client: HomeAssistantClient,
        addon_manager: AddonManager,
        history: EventHistory | None = None,
        auth_token: str | None = None,
        host: str = "0.0.0.0",
    ) -> None:
        self.hass_client = hass_client
        self.addon_manager = addon_manager
        self.history = history
        self.auth_token = auth_token
        self.host = host
        self.app = web.Application(middlewares=[auth_middleware])
        self.app[_AUTH_TOKEN_KEY] = auth_token or ""
        # Set once the TCP site is bound; lets callers confirm reachability
        # without probing the port.
        self.started = asyncio.Event()
        self._class_names = self._load_class_names()
        self.app.router.add_get("/", self.serve_index)
        self.app.router.add_get("/api/cameras", self.get_cameras)
        self.app.router.add_get("/api/microphones", self.get_microphones)
        self.app.router.add_get("/api/detections", self.get_detections)
        self.app.router.add_post("/api/source", self.set_source)
        self.app.router.add_get("/api/source", self.get_source)
        # Classifier filter endpoints
        self.app.router.add_get("/api/classifiers", self.get_classifiers)
        self.app.router.add_post("/api/classifiers", self.set_classifiers)
        self.app.router.add_get("/api/class-map", self.get_class_map)

    def _log_bind_notice(self, host: str, port: int) -> None:
        """Warn appropriately about an unauthenticated non-loopback bind."""
        if host == "127.0.0.1" or self.auth_token:
            return
        if os.getenv("SUPERVISOR_TOKEN"):
            # Running as a Home Assistant add-on: ingress authenticates
            # every request before it reaches us, so an open bind is fine.
            _LOGGER.debug(
                "Web UI bound to %s:%s behind Home Assistant ingress", host, port
            )
        else:
            _LOGGER.warning(
                "Web UI is bound to %s without an auth token; anyone who "
                "can reach this port can change the audio source and "
                "restart the add-on. Set 'webui.auth_token' when exposing "
                "it outside Home Assistant ingress.",
                host,
            )

    async def start(self, host: str = "0.0.0.0", port: int = 8099) -> None:
        """Start the aiohttp web server and run until cancelled."""
        self._log_bind_notice(host, port)
        runner = web.AppRunner(self.app)
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        _LOGGER.info("Web UI server starting on %s:%s", host, port)
        await site.start()
        self.started.set()
        _LOGGER.info("Web UI server started successfully")
        try:
            # Wait forever until cancelled (e.g. when the detection loop
            # ends and asyncio.gather tears everything down).
            await asyncio.Future()
        except asyncio.CancelledError:
            _LOGGER.info("Web UI server shutting down")
            await runner.cleanup()
            raise

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
        .filter-controls {
            margin-top: 20px;
            padding-top: 15px;
            border-top: 1px solid #eee;
        }
        .filter-row {
            margin-bottom: 15px;
        }
        .filter-row:last-child {
            margin-bottom: 0;
        }
        .filter-controls label {
            font-style: italic;
            display: block;
            margin-bottom: 3px;
            font-weight: 400;
            color: #666;
        }
        .filter-controls select {
            height: 110px;
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
        <h1>🎤🎵 HA Audio Events</h1>
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

        <div class="form-group" style="margin-top: 30px; border-top: 1px solid #eee; padding-top: 20px;">
            <label>Recent Detections</label>
            <div id="detections-list" style="max-height: 240px; overflow-y: auto;">
                <div class="loading">Waiting for detections...</div>
            </div>
        </div>

        <div class="form-group" style="margin-top: 20px;">
            <h3>Audio Class Filters</h3>
            <p class="subtitle">Choose which detected sounds are reported (from the YAMNet label list).</p>
            <form id="filters-form">
                <div class="filter-row">
                    <label for="include-select">Include (empty = report all classes)</label>
                    <select id="include-select" multiple></select>
                </div>
                <div class="filter-row">
                    <label for="exclude-select">Exclude</label>
                    <select id="exclude-select" multiple></select>
                </div>
                <button type="submit" id="filters-btn">Apply Filters</button>
            </form>
        </div>
    </div>

    <script>
        let cameras = [];
        let microphones = [];
        let currentSource = '';
        let isLoading = true;

        // When the panel is protected by a webui auth token (standalone
        // deployments), prompt once, remember it for this browser, and send
        // it on every API call.
        function getStoredToken() {
            try {
                return sessionStorage.getItem('webui_token') || '';
            } catch (e) {
                return '';
            }
        }

        async function apiFetch(url, opts = {}) {
            const headers = Object.assign({}, opts.headers || {});
            const token = getStoredToken();
            if (token) {
                headers['X-WebUI-Token'] = token;
            }
            const response = await fetch(url, Object.assign({}, opts, { headers: headers }));
            if (response.status === 401) {
                const entered = prompt('This Web UI is protected. Enter the auth token:');
                if (entered !== null && entered !== '') {
                    try {
                        sessionStorage.setItem('webui_token', entered);
                    } catch (e) { /* storage unavailable */ }
                    return apiFetch(url, opts);
                }
                throw new Error('Unauthorized');
            }
            return response;
        }

        // Parse a panel API response defensively. When the add-on is stopped
        // or mid-restart, the ingress proxy answers with its own HTML/plain
        // error page -- calling .json() on that produced cryptic errors like
        // "Unexpected non-whitespace character after JSON".
        async function parseApiResponse(response, what) {
            const contentType = response.headers.get('content-type') || '';
            const bodyText = await response.text();
            if (!contentType.includes('application/json')) {
                const snippet = bodyText.trim().slice(0, 100);
                throw new Error(
                    'The add-on does not appear to be running' +
                    (snippet ? ` (proxy said: "${snippet}")` : '') +
                    ' - start it from Settings > Add-ons and reload.'
                );
            }
            try {
                return JSON.parse(bodyText);
            } catch (e) {
                throw new Error(`Received malformed data for ${what}`);
            }
        }

        // Load initial data
        async function loadData() {
            try {
                // Load cameras
                const camerasResponse = await apiFetch('api/cameras');
                if (!camerasResponse.ok) {
                    throw new Error(`Failed to load cameras (HTTP ${camerasResponse.status})`);
                }
                cameras = await parseApiResponse(camerasResponse, 'cameras');

                // Load microphones (voice satellites) -- best-effort, don't
                // fail the whole page if this one endpoint has an issue
                try {
                    const micResponse = await apiFetch('api/microphones');
                    if (micResponse.ok) {
                        microphones = await parseApiResponse(micResponse, 'microphones');
                    }
                } catch (micError) {
                    console.warn('Failed to load microphones:', micError);
                }

                // Load current source
                const sourceResponse = await apiFetch('api/source');
                if (sourceResponse.ok) {
                    const data = await parseApiResponse(sourceResponse, 'current source');
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

            if (cameras.length === 0 && microphones.length === 0) {
                select.innerHTML = '<option value="">No entities found</option>';
            }

            if (cameras.length > 0) {
                const cameraGroup = document.createElement('optgroup');
                cameraGroup.label = 'Cameras';
                cameras.forEach(camera => {
                    const option = document.createElement('option');
                    option.value = camera.entity_id;
                    option.textContent = `${camera.friendly_name} (${camera.entity_id})`;
                    cameraGroup.appendChild(option);
                });
                select.appendChild(cameraGroup);
            }

            if (microphones.length > 0) {
                const micGroup = document.createElement('optgroup');
                micGroup.label = 'Voice Satellites (not yet supported as a capture source)';
                microphones.forEach(mic => {
                    const option = document.createElement('option');
                    option.value = mic.entity_id;
                    option.textContent = `${mic.friendly_name} (${mic.entity_id})`;
                    option.disabled = true;
                    micGroup.appendChild(option);
                });
                select.appendChild(micGroup);
            }

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

        let allClasses = [];

        // Load YAMNet class names and current include/exclude selections,
        // then populate both multi-select dropdowns.
        async function loadFilters() {
            try {
                const mapResponse = await apiFetch('api/class-map');
                if (mapResponse.ok) {
                    const data = await parseApiResponse(mapResponse, 'class map');
                    allClasses = data.classes || [];
                }

                let current = { include: [], exclude: [] };
                const filtersResponse = await apiFetch('api/classifiers');
                if (filtersResponse.ok) {
                    current = await parseApiResponse(filtersResponse, 'classifier filters');
                }

                populateClassSelect(current.include || [], current.exclude || []);
            } catch (error) {
                console.warn('Failed to load classifier filters:', error);
            }
        }

        function populateClassSelect(includeSelected, excludeSelected) {
            const includeSel = document.getElementById('include-select');
            const excludeSel = document.getElementById('exclude-select');

            includeSel.innerHTML = '';
            excludeSel.innerHTML = '';

            allClasses.forEach(name => {
                const value = name.toLowerCase();

                const incOpt = document.createElement('option');
                incOpt.value = value;
                incOpt.textContent = name;
                if (includeSelected.includes(value)) { incOpt.selected = true; }
                includeSel.appendChild(incOpt);

                const excOpt = document.createElement('option');
                excOpt.value = value;
                excOpt.textContent = name;
                if (excludeSelected.includes(value)) { excOpt.selected = true; }
                excludeSel.appendChild(excOpt);
            });
        }

        async function applyFilters(e) {
            e.preventDefault();

            const btn = document.getElementById('filters-btn');
            const originalText = btn.textContent;
            btn.disabled = true;
            btn.textContent = 'Applying...';

            try {
                const include = Array.from(document.getElementById('include-select').selectedOptions)
                    .map(o => o.value);
                const exclude = Array.from(document.getElementById('exclude-select').selectedOptions)
                    .map(o => o.value);

                const response = await apiFetch('api/classifiers', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ include: include, exclude: exclude })
                });

                if (response.ok) {
                    await parseApiResponse(response, 'apply filters result');
                    showMessage('Audio class filters updated!', 'success');
                    showStatus('Filters applied. The add-on is restarting to apply changes.', 'success');
                } else {
                    const error = await parseApiResponse(response, 'error details');
                    showMessage(`Error: ${error.error || 'Failed to update filters'}`, 'error');
                }
            } catch (error) {
                showMessage(`${error.message}`, 'error');
            } finally {
                btn.disabled = false;
                btn.textContent = originalText;
            }
        }

        function renderDetections(detections) {
            const list = document.getElementById('detections-list');
            if (!detections || detections.length === 0) {
                list.innerHTML = '<div class="loading">Waiting for detections...</div>';
                return;
            }

            // Build rows via textContent (never innerHTML) so label/state
            // values can't inject markup into the panel.
            list.innerHTML = '';
            detections.forEach(d => {
                const row = document.createElement('div');
                row.style.cssText = 'padding: 8px 10px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; font-size: 14px;';

                const left = document.createElement('span');
                const strong = document.createElement('strong');
                strong.textContent = d.label;
                const detail = document.createElement('span');
                detail.style.color = '#888;';
                const confidencePct = Math.round((d.confidence || 0) * 100);
                detail.textContent = ` (${d.state}, ${confidencePct}%)`;
                left.appendChild(strong);
                left.appendChild(detail);

                const right = document.createElement('span');
                right.style.color = '#888;';
                right.textContent = new Date(d.timestamp).toLocaleTimeString();

                row.appendChild(left);
                row.appendChild(right);
                list.appendChild(row);
            });
        }

        async function pollDetections() {
            try {
                const response = await apiFetch('api/detections');
                if (response.ok) {
                    const detections = await parseApiResponse(response, 'detections');
                    renderDetections(detections);
                }
            } catch (error) {
                // Silent-ish: the panel polls every 3s and transient errors
                // (add-on restarting) must not spam red banners.
                console.warn('Failed to poll detections:', error);
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

                const response = await apiFetch('api/source', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ source: source })
                });

                if (response.ok) {
                    await parseApiResponse(response, 'apply result');
                    showMessage('Audio source configured successfully!', 'success');
                    showStatus('Configuration applied. The add-on is restarting to apply changes.', 'success');
                    currentSource = source;
                    updateCurrentSourceDisplay();
                } else {
                    const error = await parseApiResponse(response, 'error details');
                    showMessage(`Error: ${error.error || 'Failed to configure source'}`, 'error');
                    showStatus(`Error: ${error.error || 'Failed to configure source'}`, 'error');
                }
            } catch (error) {
                // Two normal situations land here:
                // 1. The add-on was restarting while we submitted -- the
                //    request may still have been applied.
                // 2. The add-on is stopped entirely (ingress proxy error).
                if (error instanceof TypeError) {
                    showMessage(
                        'Connection lost while applying the source - the add-on is probably restarting. Reload this page in a few seconds to check.',
                        'error'
                    );
                } else {
                    showMessage(`${error.message}`, 'error');
                }
                showStatus(`${error.message}`, 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            }
        });

        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {
            loadData();
            loadFilters();
            document.getElementById('filters-form').addEventListener('submit', applyFilters);
            pollDetections();
            setInterval(pollDetections, 3000);
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
                    attributes = entity.get("attributes", {}) or {}
                    cameras.append(
                        {
                            "entity_id": entity["entity_id"],
                            "friendly_name": attributes.get(
                                "friendly_name", entity["entity_id"]
                            ),
                        }
                    )

            return web.json_response(cameras)
        except Exception as e:
            _LOGGER.exception("Error fetching cameras")
            return web.json_response({"error": str(e)}, status=500)

    async def get_microphones(self, request: web.Request) -> web.Response:
        """Fetch assist_satellite (voice-satellite / built-in microphone)
        entities from Home Assistant.

        NOTE: these are listed for visibility only. Unlike cameras, Home
        Assistant does not expose a generic pull-able audio stream URL for
        assist_satellite entities -- their audio is pushed into HA's Assist
        pipeline over ESPHome's native API protocol, not a URL ffmpeg can
        connect to. Selecting one here is rejected by set_source with an
        explanation, rather than silently accepting a source_path the
        pipeline can't actually read from.
        """
        try:
            state = await self.hass_client.get_state("assist_satellite")
            if state is None:
                return web.json_response(
                    {"error": "Failed to fetch microphone states"}, status=500
                )

            microphones = []
            for entity in state:
                if isinstance(entity, dict) and entity.get("entity_id", "").startswith(
                    "assist_satellite."
                ):
                    attributes = entity.get("attributes", {}) or {}
                    microphones.append(
                        {
                            "entity_id": entity["entity_id"],
                            "friendly_name": attributes.get(
                                "friendly_name", entity["entity_id"]
                            ),
                        }
                    )

            return web.json_response(microphones)
        except Exception as e:
            _LOGGER.exception("Error fetching microphones")
            return web.json_response({"error": str(e)}, status=500)

    async def get_detections(self, request: web.Request) -> web.Response:
        """Return the most recent detection events, most recent first."""
        if self.history is None:
            return web.json_response([])
        return web.json_response(self.history.recent())

    async def get_source(self, request: web.Request) -> web.Response:
        """Get the currently configured source path."""
        try:
            source = await self.addon_manager.get_option("audio", "source_path")
            return web.json_response({"source": source or ""})
        except Exception as e:
            _LOGGER.exception("Error fetching source")
            return web.json_response({"error": str(e)}, status=500)

    async def set_source(self, request: web.Request) -> web.Response:
        """Set the audio source path and restart the add-on.

        The HTTP response is sent BEFORE the restart is triggered: restarting
        kills this container, and answering afterwards would hand the browser
        a truncated/non-JSON body (seen as "Unexpected non-whitespace
        character after JSON" in the panel).
        """
        try:
            data = await request.json()
            source = data.get("source")
            if not source:
                return web.json_response(
                    {"error": "Missing source parameter"}, status=400
                )

            if str(source).startswith("assist_satellite."):
                return web.json_response(
                    {
                        "error": (
                            "Voice satellite entities aren't supported as an "
                            "audio source yet. Home Assistant doesn't expose "
                            "a pull-able audio stream for assist_satellite "
                            "entities the way it does for cameras -- their "
                            "audio goes to HA's Assist pipeline over "
                            "ESPHome's native protocol, not a URL this "
                            "add-on can read from directly."
                        )
                    },
                    status=400,
                )

            success = await self.addon_manager.set_option(
                "audio", "source_path", source
            )
            if not success:
                return web.json_response(
                    {"error": "Failed to set source in add-on options"}, status=500
                )

            asyncio.create_task(self._delayed_restart())

            _LOGGER.info(
                "Audio source configured to %s; restarting add-on in %ss",
                source,
                self.RESTART_DELAY,
            )
            return web.json_response(
                {
                    "status": "success",
                    "message": "Source configured; add-on is restarting",
                }
            )

        except Exception as e:
            _LOGGER.exception("Error setting source")
            return web.json_response({"error": str(e)}, status=500)

    RESTART_DELAY: float = 1.0

    async def _delayed_restart(self) -> None:
        """Restart the add-on after the current response has been delivered."""
        try:
            await asyncio.sleep(self.RESTART_DELAY)
            await self.addon_manager.restart()
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("Delayed add-on restart failed")

    def _load_class_names(self) -> list[str]:
        """Load YAMNet class names from the class map CSV.

        Same lookup convention as YAMNetClassifier._load_labels(): the class
        map sits next to the model, resolved relative to the add-on's
        working directory. Loaded once at startup; the file is ~30 KB.
        """
        csv_path = Path("models/yamnet_class_map.csv")
        if not csv_path.exists():
            _LOGGER.warning("Class map CSV not found at %s", csv_path)
            return []
        classes: list[str] = []
        try:
            with csv_path.open("r", encoding="utf-8", newline="") as handle:
                for row in csv.DictReader(handle):
                    display_name = (row.get("display_name") or "").strip()
                    if display_name and display_name not in classes:
                        classes.append(display_name)
        except Exception:
            _LOGGER.exception("Error loading class map CSV")
        return classes

    async def get_class_map(self, request: web.Request) -> web.Response:
        """Return the list of audio class names for filter dropdowns."""
        return web.json_response({"classes": self._class_names})

    async def get_classifiers(self, request: web.Request) -> web.Response:
        """Get current include/exclude filter lists."""
        try:
            include = await self.addon_manager.get_option("classifier", "include") or []
            exclude = await self.addon_manager.get_option("classifier", "exclude") or []
            return web.json_response(
                {
                    "include": [str(item).lower() for item in include],
                    "exclude": [str(item).lower() for item in exclude],
                }
            )
        except Exception as e:
            _LOGGER.exception("Error fetching classifier filters")
            return web.json_response({"error": str(e)}, status=500)

    async def set_classifiers(self, request: web.Request) -> web.Response:
        """Set include/exclude filter lists and restart the add-on."""
        try:
            data = await request.json()

            include_raw = data.get("include", [])
            exclude_raw = data.get("exclude", [])
            if not isinstance(include_raw, list) or not isinstance(exclude_raw, list):
                return web.json_response(
                    {"error": "include and exclude must be lists of strings"},
                    status=400,
                )
            include = [
                str(item).strip().lower() for item in include_raw if str(item).strip()
            ]
            exclude = [
                str(item).strip().lower() for item in exclude_raw if str(item).strip()
            ]

            success = await self.addon_manager.set_option(
                "classifier", "include", include
            )
            if not success:
                return web.json_response(
                    {"error": "Failed to set include filter"}, status=500
                )

            success = await self.addon_manager.set_option(
                "classifier", "exclude", exclude
            )
            if not success:
                return web.json_response(
                    {"error": "Failed to set exclude filter"}, status=500
                )

            asyncio.create_task(self._delayed_restart())
            _LOGGER.info(
                "Classifier filters updated; restarting add-on in %ss",
                self.RESTART_DELAY,
            )
            return web.json_response(
                {
                    "status": "success",
                    "message": "Filters updated; add-on is restarting",
                }
            )
        except Exception as e:
            _LOGGER.exception("Error setting classifier filters")
            return web.json_response({"error": str(e)}, status=500)
