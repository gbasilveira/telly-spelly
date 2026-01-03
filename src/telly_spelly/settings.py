from PyQt6.QtCore import QSettings
import json

class Settings:
    ALL_MODELS = ['tiny', 'base', 'small', 'medium', 'large', 'turbo']
    VALID_MODELS = ALL_MODELS  # For backwards compatibility
    # List of valid language codes for Whisper
    VALID_LANGUAGES = {
        'auto': 'Auto-detect',
        'en': 'English',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'it': 'Italian',
        'pt': 'Portuguese',
        'nl': 'Dutch',
        'pl': 'Polish',
        'ja': 'Japanese',
        'zh': 'Chinese',
        'ru': 'Russian',
        # Add more languages as needed
    }
    
    def __init__(self):
        self.settings = QSettings('TellySpelly', 'TellySpelly')
        
    def get(self, key, default=None):
        value = self.settings.value(key, default)
        
        # Validate specific settings
        if key == 'model' and value not in self.VALID_MODELS:
            return default
        elif key == 'mic_index':
            try:
                return int(value)
            except (ValueError, TypeError):
                return default
        elif key == 'language' and value not in self.VALID_LANGUAGES:
            return 'auto'  # Default to auto-detect
                
        return value
        
    def set(self, key, value):
        # Validate before saving
        if key == 'model' and value not in self.VALID_MODELS:
            raise ValueError(f"Invalid model: {value}")
        elif key == 'mic_index':
            try:
                value = int(value)
            except (ValueError, TypeError):
                raise ValueError(f"Invalid mic_index: {value}")
        elif key == 'language' and value not in self.VALID_LANGUAGES:
            raise ValueError(f"Invalid language: {value}")
                
        self.settings.setValue(key, value)
        self.settings.sync()

    def get_available_models(self):
        """Get list of models available for current hardware"""
        models_json = self.settings.value('available_models', None)
        if models_json:
            try:
                return json.loads(models_json)
            except (json.JSONDecodeError, TypeError):
                pass
        return self.ALL_MODELS

    def set_available_models(self, models):
        """Set list of models available for current hardware"""
        self.settings.setValue('available_models', json.dumps(models))
        self.settings.sync()

    def get_gpu_memory(self):
        """Get detected GPU memory in GB, or None if CPU-only"""
        value = self.settings.value('gpu_memory_gb', None)
        if value is not None:
            try:
                return float(value)
            except (ValueError, TypeError):
                pass
        return None

    def set_gpu_memory(self, memory_gb):
        """Set detected GPU memory"""
        if memory_gb is None:
            self.settings.remove('gpu_memory_gb')
        else:
            self.settings.setValue('gpu_memory_gb', memory_gb)
        self.settings.sync()

    def is_hardware_detected(self):
        """Check if hardware detection has been performed"""
        return self.settings.value('hardware_detected', False, type=bool)

    def set_hardware_detected(self, detected=True):
        """Mark that hardware detection has been performed"""
        self.settings.setValue('hardware_detected', detected)
        self.settings.sync()

    def get_force_cpu(self):
        """Check if GPU should be disabled (force CPU mode)"""
        value = self.settings.value('force_cpu', False, type=bool)
        # Ensure we always return a boolean
        return bool(value)

    def set_force_cpu(self, force_cpu):
        """Set whether to force CPU-only mode"""
        self.settings.setValue('force_cpu', force_cpu)
        self.settings.sync()