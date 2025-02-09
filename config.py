from PySide6.QtCore import QSettings
import logging

class Config:
    def __init__(self):
        self.settings = QSettings('PromptoLab', 'PromptoLab')
        self._default_llm_api = "llm-cmd"  # Default value
        self._default_log_level = "Warning"  # Default log level

    @property
    def llm_api(self) -> str:
        """Get the configured LLM API."""
        return self.settings.value('llm_api', self._default_llm_api)

    @llm_api.setter
    def llm_api(self, value: str):
        """Set the LLM API configuration."""
        self.settings.setValue('llm_api', value)
        self.settings.sync()  # Ensure settings are written to disk

    @property
    def log_level(self) -> str:
        """Get the configured logging level."""
        return self.settings.value('log_level', self._default_log_level)

    @log_level.setter
    def log_level(self, value: str):
        """Set the logging level configuration and update logger."""
        self.settings.setValue('log_level', value)
        self.settings.sync()
        # Update the actual logging level
        level_map = {"Info": logging.INFO, "Warning": logging.WARNING, "Error": logging.ERROR}
        logging.getLogger().setLevel(level_map[value])

    def reset_llm_api(self):
        """Reset LLM API to default value."""
        self.settings.remove('llm_api')
        self.settings.sync()

    def reset_log_level(self):
        """Reset logging level to default value."""
        self.settings.remove('log_level')
        self.settings.sync()
        self.log_level = self._default_log_level

# Global config instance
config = Config()
