"""
i18n.py - Internationalization support
ONE RESPONSIBILITY: Handle text translation
"""

import locale
import json
import os

# Default language
DEFAULT_LANG = "en"

# Translation dictionary (Skeleton)
# In a real app, this would be loaded from JSON files
TRANSLATIONS = {
    "en": {
        "header_create": "CREATE NEW MULTI-BOOT USB",
        "header_update": "UPDATE EXISTING MULTI-BOOT USB",
        "error_root": "Root privileges required. Elevating...",
        "error_no_installers": "No macOS installers found!",
        "prompt_select_drive": "Select USB drive",
        "confirm_erase": "Type 'ERASE' to confirm",
    },
    "es": {
        "header_create": "CREAR NUEVO USB MULTI-ARRANQUE",
        "header_update": "ACTUALIZAR USB MULTI-ARRANQUE EXISTENTE",
        "error_root": "Se requieren privilegios de root. Elevando...",
        "error_no_installers": "¡No se encontraron instaladores de macOS!",
        "prompt_select_drive": "Seleccionar unidad USB",
        "confirm_erase": "Escriba 'ERASE' para confirmar",
    },
    "fr": {
        "header_create": "CRÉER UNE CLÉ USB MULTI-BOOT",
        "header_update": "METTRE À JOUR LA CLÉ USB EXISTANTE",
        "error_root": "Privilèges root requis. Élévation...",
        "error_no_installers": "Aucun installateur macOS trouvé !",
        "prompt_select_drive": "Sélectionner le disque USB",
        "confirm_erase": "Tapez 'ERASE' pour confirmer",
    }
}

CURRENT_LANG = DEFAULT_LANG

def detect_language():
    """Detect system language."""
    global CURRENT_LANG
    try:
        sys_lang = locale.getdefaultlocale()[0]
        if sys_lang:
            lang_code = sys_lang.split('_')[0]
            if lang_code in TRANSLATIONS:
                CURRENT_LANG = lang_code
    except:
        pass

def t(key):
    """Translate a key."""
    return TRANSLATIONS.get(CURRENT_LANG, TRANSLATIONS[DEFAULT_LANG]).get(key, key)

# Auto-detect on import
detect_language()
