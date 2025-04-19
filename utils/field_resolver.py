import os
import yaml
import logging
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration paths
CONFIG_DIR = os.path.join(os.getcwd(), "config")
DEFAULT_CONFIG = os.path.join(CONFIG_DIR, "default_field_config.yaml")
OVERRIDES_DIR = os.path.join(CONFIG_DIR, "ticket_overrides")

# Ensure directories exist
os.makedirs(OVERRIDES_DIR, exist_ok=True)


def load_yaml(path: str) -> Dict[str, Any]:
    """
    Safely load a YAML file with error handling.
    
    Args:
        path: Path to the YAML file
        
    Returns:
        Dictionary of YAML contents, empty dict if file not found or invalid
    """
    try:
        if not os.path.exists(path):
            logger.warning(f"Config file not found: {path}")
            return {}
            
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.error(f"Error loading YAML file {path}: {e}")
        return {}


def resolve_fields(ticket: str) -> Dict[str, str]:
    """
    Resolve field values for a given ticket based on default and override configs.
    
    Args:
        ticket: Jira ticket ID
        
    Returns:
        Dictionary of resolved field values
    """
    # Load configurations
    defaults = load_yaml(DEFAULT_CONFIG)
    if not defaults:
        logger.warning(f"No default configuration found at {DEFAULT_CONFIG}")
        defaults = {}  # Fallback to empty defaults
        
    override_path = os.path.join(OVERRIDES_DIR, f"{ticket}.yaml")
    overrides = load_yaml(override_path)

    # Merge configurations and resolve fields
    fields: Dict[str, str] = {}
    
    try:
        for field, cfg in defaults.items():
            if not isinstance(cfg, dict):
                logger.warning(f"Invalid configuration for field '{field}', skipping")
                continue
                
            # Get source with fallback to default
            field_overrides = overrides.get(field, {})
            src = field_overrides.get("source", cfg.get("source", "default"))
            
            try:
                if src == "ai":
                    from ai.generator import generate_summary
                    fields[field] = generate_summary(ticket)
                elif src == "ticket_id":
                    fields[field] = ticket
                elif src == "manual":
                    value = field_overrides.get("value")
                    if not value:
                        try:
                            value = input(f"Please enter value for '{field}': ")
                        except (KeyboardInterrupt, EOFError):
                            logger.warning(f"Input interrupted for field '{field}'")
                            value = ""
                    fields[field] = value
                elif src == "default":
                    fields[field] = cfg.get("value", "")
                elif src == "custom":
                    fields[field] = field_overrides.get("value", "")
                else:
                    logger.warning(f"Unknown source type '{src}' for field '{field}'")
                    fields[field] = ""
            except Exception as e:
                logger.error(f"Error resolving field '{field}': {e}")
                fields[field] = f"[Error: {str(e)[:30]}...]"
    except Exception as e:
        logger.error(f"Error during field resolution: {e}")
    
    return fields 