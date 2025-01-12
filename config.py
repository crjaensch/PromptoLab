from PySide6.QtCore import QSettings

class Config:
    def __init__(self):
        self.settings = QSettings('PromptoLab', 'PromptoLab')
        self._default_llm_api = "llm-cmd"  # Default value

    @property
    def llm_api(self) -> str:
        """Get the configured LLM API."""
        return self.settings.value('llm_api', self._default_llm_api)

    @llm_api.setter
    def llm_api(self, value: str):
        """Set the LLM API configuration."""
        self.settings.setValue('llm_api', value)
        self.settings.sync()  # Ensure settings are written to disk

    def reset_llm_api(self):
        """Reset LLM API to default value."""
        self.settings.remove('llm_api')
        self.settings.sync()

# Global config instance
config = Config()
