# PromptoLab

PromptoLab is a cross-platform desktop application for cataloging, evaluating, testing, and improving LLM prompts. It provides a playground for interactive prompt development and a test set manager for systematic prompt testing.

## Features

- **Prompt Catalog**: Create, edit, save, and select prompts for testing
- **LLM Playground**: Interactive environment for testing prompts with immediate LLM responses
- **Test Set Manager**: Create and manage test sets for systematic prompt testing
- **Eval Playground**: Evaluate LLM performance on test sets via text embeddings and LLM grading
- **Customizable Parameters**: Fine-tune LLM parameters (temperature, max_tokens, top_p)
- **System Prompts**: Support for system prompts to guide the LLM behavior

## Prerequisites

- Python 3.10 or higher
- [llm](https://github.com/simonw/llm) command-line tool
  ```bash
  pip install llm
  ```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/crjaensch/PromptoLab.git
   cd PromptoLab
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   python3 -m pip install -r requirements.txt
   ```

## Running the Application

1. Ensure your virtual environment is activated:
   ```bash
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Run the application:
   ```bash
   # If inside PromptoLab, then move to the parent directory
   cd ..
   python3 -m PromptoLab
   ```

## Usage

1. **LLM Playground**
   - Enter your prompt in the user prompt field
   - Optionally set a system prompt
   - Adjust LLM parameters (temperature, max_tokens, top_p) as needed
   - Click "Run" to see the LLM response
   - Click "Improve Prompt" to improve the current prompt using the LLM

2. **Test Set Manager**
   - Create a new test set with a name and system prompt
   - Add test cases with user prompts
   - Generate baseline outputs using current LLM settings
   - Save and load test sets for future reference

## Development

The project uses:
- PySide6 for the GUI to enable cross-platform use
- Simon Willison's `llm` tool for LLM interactions
- Python's built-in `venv` for environment management

## License

This project is licensed under the MIT License. See the [LICENSE](license.md) file in the repository for the full license text.

