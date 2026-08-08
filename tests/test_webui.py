
# Test WebUI functionality
class TestWebUI:
    async def test_webui_availability(self, async_http_client):
        client = async_http_client
        async with client.get('http://localhost:8099') as resp:
            assert resp.status == 200

    async def test_cameras_endpoint(self, async_http_client):
        client = async_http_client
        async with client.get('http://localhost:8099/api/cameras') as resp:
            assert resp.status == 200
