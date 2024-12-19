# Unit Tests for PromptoLab

This document provides an overview of the unit tests for PromptoLab, located in the `./tests` subfolder, and instructions on how to run them.

## Purpose of the Unit Tests

The unit tests in the `./tests` subfolder are designed to verify the functionality of various components of the PromptoLab application. These tests ensure that the code behaves as expected and helps in identifying any issues or bugs. The tests cover different modules and functionalities, including:

- `tests/test_collapsible_panel.py`: Tests for the `CollapsiblePanel` component.
- `tests/test_evaluation_widget.py`: Tests for the `EvaluationWidget` component.
- `tests/test_expandable_text.py`: Tests for the `ExpandableTextWidget` component.
- `tests/test_llm_playground.py`: Tests for the `LLMPlaygroundWidget` component.
- `tests/test_models.py`: Tests for the data models used in the application.
- `tests/test_output_analyzer.py`: Tests for the `OutputAnalyzer` component.
- `tests/test_prompts_catalog.py`: Tests for the `PromptsCatalogWidget` component.
- `tests/test_storage.py`: Tests for the storage functionality.
- `tests/test_test_set_manager.py`: Tests for the `TestSetManagerWidget` component.

## Setting Up the Environment

Before running the unit tests, you need to set up your Python environment and install the necessary packages. Follow these steps:

1. **Create and activate a virtual environment:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install the required packages:**

   ```bash
   python3 -m pip install -r requirements.txt
   python3 -m pip install -r requirements-dev.txt
   ```

## Running the Unit Tests

To run all the unit tests, navigate to the main folder of the project and use the following command:

```bash
pytest -v ./tests/*.py
```

This command will execute all the test files in the `./tests` subfolder and provide a detailed output of the test results.

## Additional Information

For more detailed instructions on setting up a Python virtual environment, refer to the [README.md](README.md) file in the main folder of the project.
