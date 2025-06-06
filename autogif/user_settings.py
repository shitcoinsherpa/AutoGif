import json
import os
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from autogif import config # For USER_CONFIG_FILE

# --- Pydantic Models for Settings ---

class WordEffectSettings(BaseModel):
    """Settings for word-level effects"""
    effects: Dict[str, bool] = Field(default_factory=dict)  # effect_slug -> enabled
    color: Optional[str] = None  # Override color for this word

class EffectSetting(BaseModel):
    enabled: bool = True
    intensity: int = 50

class TypographySettings(BaseModel):
    font_family: str = "Consolas"
    font_size_pt: int = 24
    font_color_hex: str = "#00FF41"
    outline_color_hex: str = "#004400"
    outline_width_px: int = 2

class UserSettings(BaseModel):
    last_youtube_url: Optional[str] = None
    last_start_time: Optional[str] = "00:00.000"
    last_end_time: Optional[str] = "00:05.000"
    last_fps: int = 12
    last_resolution: str = "480p"
    typography: TypographySettings = Field(default_factory=TypographySettings)
    effects: Dict[str, EffectSetting] = Field(default_factory=dict) # Keyed by effect slug
    # Add other settings as needed, e.g., recent_urls: List[str] = Field(default_factory=list)

# --- Load and Save Functions ---

def load_user_settings() -> UserSettings:
    """Loads user settings from the JSON file. Returns default settings if file not found or invalid."""
    try:
        if os.path.exists(config.USER_CONFIG_FILE):
            with open(config.USER_CONFIG_FILE, 'r') as f:
                data = json.load(f)
                # print(f"DEBUG: Loaded settings data: {data}") # For debugging
                # Before parsing, ensure 'effects' is a dict, not a list from older versions
                if 'effects' in data and isinstance(data['effects'], list):
                    # Attempt to convert old list format to new dict format if possible
                    # This is a basic migration, assumes list items might have a 'slug'
                    # print("DEBUG: Old list-based effects settings found, attempting migration.")
                    migrated_effects = {}
                    for item in data['effects']:
                        if isinstance(item, dict) and 'slug' in item and 'enabled' in item and 'intensity' in item:
                            migrated_effects[item['slug']] = EffectSetting(enabled=item['enabled'], intensity=item['intensity'])
                    data['effects'] = migrated_effects
                    # print(f"DEBUG: Migrated effects: {data['effects']}")
                
                return UserSettings(**data)
        # print("DEBUG: Settings file not found, returning default settings.")
        return UserSettings() # Return default settings
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        print(f"Error loading user settings from {config.USER_CONFIG_FILE}: {e}. Returning default settings.")
        return UserSettings() # Return default on error
    except Exception as e_global:
        print(f"An unexpected error occurred loading settings: {e_global}. Returning default settings.")
        return UserSettings()

def save_user_settings(settings: UserSettings) -> None:
    """Saves user settings to the JSON file."""
    try:
        os.makedirs(config.USER_CONFIG_DIR, exist_ok=True)
        with open(config.USER_CONFIG_FILE, 'w') as f:
            json.dump(settings.model_dump(mode='json'), f, indent=4)
        # print(f"DEBUG: User settings saved to {config.USER_CONFIG_FILE}")
    except Exception as e:
        print(f"Error saving user settings to {config.USER_CONFIG_FILE}: {e}")

# Example of how to initialize/update effect settings based on available plugins
# This would typically be called once at startup after loading base settings and discovering plugins.
def initialize_effect_settings(settings: UserSettings, available_effects_instances: List[Any]) -> UserSettings:
    """
    Ensures that the settings object has entries for all available effects,
    using defaults from plugins if an effect is new.
    """
    changed = False
    for effect_plugin in available_effects_instances:
        slug = effect_plugin.slug
        if slug not in settings.effects:
            settings.effects[slug] = EffectSetting(
                enabled=False, # Default new effects to disabled
                intensity=effect_plugin.default_intensity
            )
            changed = True
            # print(f"DEBUG: Initialized new effect '{slug}' in settings.")
        else:
            # Ensure existing settings are valid EffectSetting objects (in case of manual edit or corruption)
            if not isinstance(settings.effects[slug], EffectSetting):
                try:
                    # print(f"DEBUG: Re-casting effect setting for '{slug}' from {type(settings.effects[slug])}")
                    settings.effects[slug] = EffectSetting(**settings.effects[slug])
                except Exception:
                    # print(f"DEBUG: Failed to re-cast '{slug}', reverting to default.")
                    settings.effects[slug] = EffectSetting(intensity=effect_plugin.default_intensity)
                    changed = True

    # Clean up stale effect settings (effects that are no longer in plugins folder)
    # current_plugin_slugs = {p.slug for p in available_effects_instances}
    # stale_slugs = [s for s in settings.effects if s not in current_plugin_slugs]
    # for s_slug in stale_slugs:
    #     del settings.effects[s_slug]
    #     changed = True
    #     print(f"DEBUG: Removed stale effect '{s_slug}' from settings.")

    # if changed: print("DEBUG: Effect settings were modified during initialization.")
    return settings

if __name__ == '__main__':
    # Test loading and saving
    print(f"Config file path: {config.USER_CONFIG_FILE}")
    my_settings = load_user_settings()
    print("Loaded settings:", my_settings.model_dump_json(indent=2))

    # Modify something
    my_settings.last_youtube_url = "https://www.youtube.com/watch?v=test12345"
    my_settings.typography.font_size_pt = 30
    if not my_settings.effects:
         my_settings.effects["test-effect"] = EffectSetting(enabled=False, intensity=99)
    else:
        # Get first effect slug if available
        first_effect_slug = next(iter(my_settings.effects))
        my_settings.effects[first_effect_slug].intensity = 80

    save_user_settings(my_settings)
    print("\nSaved settings.")

    reloaded_settings = load_user_settings()
    print("\nReloaded settings:", reloaded_settings.model_dump_json(indent=2))

    assert reloaded_settings.last_youtube_url == "https://www.youtube.com/watch?v=test12345"
    assert reloaded_settings.typography.font_size_pt == 30
    if my_settings.effects: # if effects were present to be modified
        first_effect_slug = next(iter(my_settings.effects))
        assert reloaded_settings.effects[first_effect_slug].intensity == 80
    print("\nTests passed.") 