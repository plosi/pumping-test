from pathlib import Path
import yaml
import json

YAML_EXTENSIONS = [".yaml", ".yml"]
JSON_EXTENSIONS = [".json"]

def load_config_file(path: str | Path) -> dict:
    """
    Load a JSON or YAML config file and return its contents as a raw dict.
    File format is detected from the file extension.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the extension is unsupported, or the file cannot be parsed.
    """
    path = Path(path)
    # Check if file exists
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: '{path}'.")
    if not path.is_file():
        raise ValueError(f"'{path}' is a directory, not a file.")
    
    extension = path.suffix.lower()
    if extension in YAML_EXTENSIONS:
        result = _handle_yaml_file(path)
    elif extension in JSON_EXTENSIONS:
        result = _handle_json_file(path)
    else:
        raise ValueError(
            f"Unsupported file extension '{extension}'. "
            f"Expected one of: {YAML_EXTENSIONS | JSON_EXTENSIONS}."
        )
    return result

def _handle_yaml_file(path: str | Path) -> dict:
    """ Read a yaml file and return a raw dictionary (a dictionary of dictionaries). """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Failed to parse YAML file '{path}': {e}")
    if not isinstance(data, dict):
        raise ValueError(f"YAML file '{path}' must contain a mapping at the top level, got {type(data).__name__}.")
    return data

def _handle_json_file(path: str | Path) -> dict:
    """ Read a json file and return a raw dictionary. """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON file '{path}': {e}")
    if not isinstance(data, dict):
        raise ValueError(f"JSON file '{path}' must contain an object at the top level, got {type(data).__name__}.")
    return data