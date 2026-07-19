import logging
import time

logger = logging.getLogger(__name__)

class ModelManager:
    def __init__(self, config):
        self.config = config.get('models', {})
        self.active_model = None
        self.last_activity = time.time()
        self.loaded_models = {} # model_id -> status

    async def get_endpoint(self, model_name: str):
        """Returns the endpoint for a given model name."""
        model_info = self.config.get(model_name)
        if not model_info:
            logger.error(f"Model {model_name} not found in config")
            return None
        return model_info.get('endpoint')

    async def ensure_model_loaded(self, model_name: str):
        """Simulates loading a model if not already active."""
        if self.active_model == model_name:
            self.last_activity = time.time()
            return True
        
        logger.info(f"Switching to model: {model_name}")
        # In a real implementation, this would trigger the model server (e.g., via cookbook/vLLM)
        self.active_model = model_name
        self.last_activity = time.time()
        self.loaded_models[model_name] = "running"
        return True

    async def check_idle_timeout(self, timeout_minutes: int):
        """Unloads model if idle for too long."""
        if self.active_model and (time.time() - self.last_activity) > (timeout_minutes * 60):
            logger.info(f"Model {self.active_model} idle timeout reached. Unloading...")
            self.active_model = None
            return True
        return False

    def get_status(self):
        return {
            "active_model": self.active_model,
            "last_activity": time.ctime(self.last_activity),
            "loaded_models": self.loaded_models
        }
