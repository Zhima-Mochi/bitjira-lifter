from typing import Dict

def apply_template(template_path: str, context: Dict[str, str]) -> str:
    template_text = open(template_path, "r").read()
    return template_text.format(**context) 