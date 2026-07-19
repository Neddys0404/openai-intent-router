import yaml
from typing import Dict, Any

class ModelManager:
    def __init__(self, config_path: str = "ai-gateway/config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        self.models = self.config.get('models', {})

    async def get_endpoint(self, model_name: str) -> str:
        model_info = self.models.get(model_name)
        if not model_info:
            raise ValueError(f"Model '{model_name}' not found in config.")
        return model_info.get('endpoint')

    async def is_running(self, model_name: str) -> bool:
        # Placeholder for actual check
        return False

    async def load_model(self, model_name: str):
        # Placeholder for launching a model via shell or API
        pass

    async def unload_model(self, model_name: str):
        # Placeholder for unloading
        pass

model_manager = ModelManager()
