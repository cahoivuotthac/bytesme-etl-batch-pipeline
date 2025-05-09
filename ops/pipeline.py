from config.logger_config import setup_logger

logger = setup_logger("transform_pipeline.log")

class TransformPipeline:
	def __init__(self, config_path: str = "config/etl_config.yml"):
		self.config = self._load_config(config_path)
		it 