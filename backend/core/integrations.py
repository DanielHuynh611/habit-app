"""Registry for explicitly configured integration clients."""


class IntegrationRegistry:
    def __init__(self):
        self._clients = {}

    def register(self, integration_id, client):
        if integration_id in self._clients:
            raise RuntimeError(f"duplicate_integration:{integration_id}")
        self._clients[integration_id] = client

    def require(self, integration_id):
        if integration_id not in self._clients:
            raise RuntimeError(f"integration_not_configured:{integration_id}")
        return self._clients[integration_id]


integration_registry = IntegrationRegistry()
