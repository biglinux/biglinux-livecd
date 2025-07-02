from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class LanguageSelection:
    """Stores data from the selected language entry."""
    code: str
    name: str
    url_params: Dict[str, str]

@dataclass
class SetupConfig:
    """Holds the complete configuration state for the wizard."""
    language: Optional[LanguageSelection] = None
    keyboard_layout: Optional[str] = None
    desktop_layout: Optional[str] = None
    theme: Optional[str] = None
    enable_jamesdsp: bool = False
    enable_enhanced_contrast: bool = False
