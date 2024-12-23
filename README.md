# PromptoLab

PromptoLab is a cross-platform desktop application for cataloging, evaluating, testing, and improving LLM prompts. It provides a playground for interactive prompt development and a test set manager for systematic prompt testing.

## Features

- **Prompt Catalog**: Create, edit, save, and select prompts for testing
- **LLM Playground**: Interactive environment for testing prompts with immediate LLM responses
- **Test Set Manager**: Create and manage test sets for systematic prompt testing
- **Eval Playground**: Evaluate LLM performance on test sets via text embeddings and LLM grading
- **Customizable Parameters**: Fine-tune LLM parameters (temperature, max_tokens, top_p)
- **System Prompts**: Support for system prompts to guide the LLM behavior

## Application Screenshots

Here's a quick visual overview of PromptoLab's main features:

### Prompts Catalog
![Prompts Catalog for managing your prompt library](images/Prompts-Catalog-Screen.png)

### LLM Playground - Submit Prompt
![Interactive LLM Playground for prompt development](images/LLM-Playground-Screen_Submit-Prompt.png)

### LLM Playground - Improve Prompt
![Interactive LLM Playground for prompt development](images/LLM-Playground-Screen_Improve-Prompt.png)

### Test Set Manager
![Test Set Manager for systematic prompt test set definition](images/TestSet-Manager-Screen.png)

### Eval Playground
![Evaluation Playground for assessing prompt performance](images/Eval-Playground-Screen.png)

### Evaluation Results Report
![HTML results report for an evaluation run](images/Eval-HTML-Report-Screen.png)

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
### Key Features

- **Prompts Catalog**: Seamlessly define and organize prompts using three distinct prompt categories. This centralized hub ensures your prompts are always accessible and well-structured for easy reuse.

- **LLM Playground**: Dive into experimentation with two dynamic options. Choose to submit a selected prompt from your catalog or request improvements for a given prompt using one of three proven prompt patterns. Customize your experience further by selecting your preferred LLM model and tweaking three critical LLM control parameters.

- **Prompts Test Set Manager**: Simplify testing of complex system prompts in generative AI applications. Define and manage test cases to ensure your system prompt guides LLM responses effectively across various user prompts.

- **Evaluation Playground**: Assess the impact of prompt adjustments with ease. This powerful tool helps you evaluate whether modifications to a system prompt enhance or hinder LLM responses across diverse user scenarios, giving you the confidence to optimize with precision.

With PromptoLab, navigating the complexities of prompt design has never been more intuitive or exciting. Ready to optimize your prompt performance? Dive into PromptoLab today!

## Development

The project uses:
- PySide6 for the GUI to enable cross-platform use
- Simon Willison's `llm` tool for LLM interactions
- Python's built-in `venv` for environment management

## License

This project is licensed under the MIT License. See the [LICENSE](license.md) file in the repository for the full license text.
