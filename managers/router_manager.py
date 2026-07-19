import logging

logger = logging.getLogger(__name__)

class RouterManager:
    def __init__(self, config):
        self.routes = config.get('routes', {})
        self.default_model = config.get('default_model')

    async def resolve_route(self, intent_or_capability: str):
        """Determines which model to use based on intent."""
        # 1. Check if it's an explicit route (e.g., "coding" -> "coder")
        if intent_or_capability in self.routes:
            route = self.routes[intent_or_capability]
            if isinstance(route, dict) and 'model' in route:
                return route['model']
            # Workflow handling could be implemented here for complex routes
            
        # 2. Fallback to default model
        return self.default_model
