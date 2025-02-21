import yaml
from pathlib import Path

 
class Configuration:
    @staticmethod
    def load(filepath="config.yml"):
        resolved_path  = Path(filepath).resolve()
        with open(resolved_path, "r") as file:
            config = yaml.safe_load(file)
            return config