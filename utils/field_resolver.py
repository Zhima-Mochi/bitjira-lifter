import os
import yaml
from typing import Dict

CONFIG_DIR = os.path.join(os.getcwd(), "config")
DEFAULT_CONFIG = os.path.join(CONFIG_DIR, "default_field_config.yaml")
OVERRIDES_DIR = os.path.join(CONFIG_DIR, "ticket_overrides")


def load_yaml(path: str) -> Dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def resolve_fields(ticket: str) -> Dict[str, str]:
    """
    Resolve field values for a given ticket based on default and override configs.
    """
    defaults = load_yaml(DEFAULT_CONFIG)
    override_path = os.path.join(OVERRIDES_DIR, f"{ticket}.yaml")
    overrides = load_yaml(override_path) if os.path.exists(override_path) else {}

    fields: Dict[str, str] = {}
    for field, cfg in defaults.items():
        src = overrides.get(field, {}).get("source", cfg.get("source"))
        if src == "ai":
            from ai.generator import generate_summary
            fields[field] = generate_summary(ticket)
        elif src == "ticket_id":
            fields[field] = ticket
        elif src == "manual":
            value = overrides.get(field, {}).get("value")
            if not value:
                value = input(f"Please enter value for '{field}': ")
            fields[field] = value
        elif src == "default":
            fields[field] = cfg.get("value", "")
        elif src == "custom":
            fields[field] = overrides[field]["value"]
        else:
            fields[field] = ""
    return fields 