# PromptoLab System Specification

**Version**: 1.0  
**Date**: 2026-01-10  
**Spec ID**: SPEC-20260110-0001  
**Depth**: Quick MVP  
**Status**: Draft

---

## 1. Overview

### 1.1 Problem Statement

Prompt engineers face a critical challenge: **detecting quality regression when prompts change**. Without systematic evaluation, modifications to prompts, system instructions, or model selection can silently degrade output quality. Manual testing is inconsistent and doesn't scale. PromptoLab provides a structured environment to establish baselines, run comparative evaluations, and quantify the impact of changes before they reach production.

### 1.2 Goals

- **G-001**: Enable systematic comparison of LLM outputs against established baselines
- **G-002**: Provide quantitative metrics (similarity scores) and qualitative feedback (LLM grader) for evaluation
- **G-003**: Support rapid prompt iteration with immediate feedback in the playground
- **G-004**: Maintain organized prompt storage with categorization and search
- **G-005**: Generate shareable evaluation reports for documentation and review

### 1.3 Non-Goals

- **NG-001**: Real-time collaboration - PromptoLab is a single-user desktop application; multi-user simultaneous editing is out of scope
- **NG-002**: Version control integration - Prompts are stored as files but Git integration is not built-in
- **NG-003**: Production deployment - This is a development/testing tool, not a runtime prompt serving system

### 1.4 Summary

PromptoLab is a desktop application for managing, testing, and optimizing LLM prompts. It provides a comprehensive environment for prompt engineering workflows including prompt storage, interactive testing, baseline comparison, and systematic evaluation.

---

## 2. User Context

### 2.1 Target Users

**Primary User**: Prompt Engineers
- Characteristics: Professionals optimizing prompts for production LLM systems
- Technical proficiency: High (comfortable with APIs, model parameters, evaluation metrics)
- Usage frequency: Daily during active prompt development cycles

### 2.2 Key Workflows

1. **Evaluate Prompt Changes** (Primary Workflow)
   - Trigger: Need to test impact of prompt modification or model change
   - Steps: Load test set → Modify prompt/model configuration → Run evaluation → Compare results against baseline
   - Outcome: Quantified assessment of whether changes improve, maintain, or degrade output quality

2. **Build Test Baselines**
   - Trigger: New prompt ready for production or establishing quality benchmark
   - Steps: Create test cases with representative inputs → Generate baseline outputs → Save test set
   - Outcome: Reusable test set for future regression testing

3. **Optimize a Prompt**
   - Trigger: Prompt underperforming or needs improvement
   - Steps: Load prompt in playground → Test with various inputs → Apply improvement patterns (TAG/PIC/LIFE) or Critique & Refine → Save refined version
   - Outcome: Improved prompt saved to catalog

---

## 3. Core Modules

The system consists of four primary functional modules:
- **Prompts Catalog** - Prompt storage and management
- **LLM Playground** - Interactive prompt execution and optimization
- **Test Set Manager** - Test case creation and baseline generation
- **Eval Playground** - Comparative evaluation and quality analysis

---

## 4. Prompts Catalog

### 4.1 Purpose
Central repository for storing, organizing, and managing reusable prompts.

### 4.2 Prompt Data Model
Each prompt contains:
- **Title**: Unique identifier for the prompt
- **User Prompt**: The main prompt text sent to the LLM
- **System Prompt**: Optional context/instructions for the LLM (nullable)
- **Prompt Type**: Classification category (see 4.3)
- **Created At**: Timestamp of creation
- **Updated At**: Timestamp of last modification
- **ID**: Unique identifier (UUID-based filename)

### 4.3 Prompt Types
Prompts are classified into three categories:
- **Simple Prompt**: Basic single-purpose prompts
- **Structured Prompt**: Prompts with defined sections or formats
- **Prompt Template**: Parameterized prompts with variable placeholders

### 4.4 Template Variables
The system supports parameterized prompts through template variables:
- Variables use double curly brace syntax: `{{variable-name}}`
- Variables are automatically detected and parsed from prompt text
- Variables can appear in both system and user prompts
- Variable values are provided at execution time
- Multiple occurrences of the same variable share a single value

### 4.5 Storage
- Prompts are persisted as JSON files in a file-based storage system
- Directory structure organizes prompts by type: `prompts/{type}/`
- Filenames combine sanitized title prefix with UUID: `{title_prefix}_{uuid}.json`

### 4.6 Operations
- **Create**: Generate new prompts with automatic UUID assignment
- **Read**: Load individual prompts or list all prompts
- **Update**: Modify existing prompts with type migration support
- **Delete**: Remove prompts from storage
- **Search**: Filter prompts by title (case-insensitive)

---

## 5. LLM Playground

### 5.1 Purpose
Interactive environment for executing prompts against LLM models and optimizing prompt quality.

### 5.2 Prompt Execution
The playground supports:
- Selection of prompts from the Prompts Catalog
- Direct prompt input and editing
- Optional system prompt configuration
- Template variable substitution before execution

### 5.3 Model Configuration
Configurable parameters for LLM requests:
- **Model Selection**: Dynamic list from configured LLM provider
- **Temperature**: Controls response randomness (optional, values: 0.0-1.0)
- **Max Tokens**: Response length limit (optional, values: 512-8192)
- **Top P**: Nucleus sampling parameter (optional, values: 0.1-1.0)

All parameters are optional; when not specified, provider defaults apply.

### 5.4 LLM Provider Integration
The system supports multiple LLM backends:
- **llm-cmd**: Integration via Simon Willison's `llm` command-line tool
- **litellm**: Direct API integration via LiteLLM library

Provider selection is configurable at the application level.

### 5.5 Prompt Optimization
Built-in prompt improvement capabilities:
- **Pattern-based Improvement**: TAG, PIC, and LIFE prompt patterns
- **Critique & Refine**: Iterative improvement through self-critique
  - Configurable number of refinement iterations
  - Combines system and user prompts for holistic optimization

### 5.6 Response Handling
- Markdown rendering for formatted output
- Syntax highlighting for code blocks
- Character and token count display
- Copy functionality for responses
- Option to save improved prompts back to catalog

---

## 6. Test Set Manager

### 6.1 Purpose
Create and manage test sets for systematic prompt evaluation.

### 6.2 Test Set Structure
A test set contains:
- **Name**: Identifier for the test set
- **System Prompt**: Shared context for all test cases
- **Test Cases**: Collection of input/output pairs

### 6.3 Test Case Data Model
Each test case includes:
- **Input Text**: The user prompt/input for the test
- **Baseline Output**: Expected/reference output
- **Current Output**: Latest generated output (for comparison)
- **Test ID**: Unique identifier
- **Created At**: Creation timestamp
- **Last Run**: Timestamp of last execution

### 6.4 Baseline Generation
- Automated generation of baseline outputs using configured LLM
- Uses shared model parameters (model, temperature, max tokens, top P)
- Sequential processing with progress tracking
- Per-case error handling with continuation support

### 6.5 Persistence
- Test sets are saved/loaded as JSON files
- Includes all test cases with their baseline outputs

---

## 7. Eval Playground

### 7.1 Purpose
Comparative evaluation of prompt performance against established baselines.

### 7.2 Evaluation Process
1. Select a test set for evaluation
2. Configure model and optional system prompt modifications
3. Execute all test cases against the selected model
4. Compare generated outputs with baseline outputs
5. Calculate quality metrics and generate analysis

### 7.3 Quality Metrics
The evaluation system calculates:
- **Semantic Similarity Scores**: Measure of output similarity to baseline
- **LLM Evaluation Grades**: AI-generated quality assessments

### 7.4 Analysis Features
For each evaluated test case:
- Side-by-side comparison of baseline and generated outputs
- Similarity metrics calculation
- LLM-grader generated structured feedback
- Detailed inspection of differences

### 7.5 Report Generation
Export evaluation results as reports containing:
- Test set identification
- Model and system prompt configurations
- Complete evaluation results per test case
- Similarity scores and LLM grades
- Self-contained format for sharing

---

## 8. Configuration and State Management

### 8.1 Application Configuration
Persistent settings include:
- **LLM API**: Selected provider (llm-cmd or litellm)
- **Log Level**: Application logging verbosity (Info, Warning, Error)

### 8.2 Session State Persistence
The application maintains state between sessions:
- Selected model and LLM parameters
- System prompt visibility and content
- Panel expansion states
- Last selected prompt
- Test set configurations

### 8.3 Shared Settings
Certain settings are synchronized across modules:
- Model selection (Playground ↔ Eval Playground)
- LLM parameters (Temperature, Max Tokens, Top P)
- System prompt configurations

---

## 9. Error Handling

### 9.1 LLM-Specific Errors
The system handles:
- **Quota Errors**: API rate limiting or usage exhaustion
- **Capability Errors**: Model feature limitations
- **Connection Errors**: Network or API connectivity issues

### 9.2 General Error Handling
- Validation errors for missing required fields
- File I/O errors for storage operations
- Graceful degradation with user feedback

---

## 10. Technical Architecture

### 10.1 Technology Stack
- **Framework**: PySide6 (Qt for Python)
- **Storage**: File-based JSON persistence
- **Threading**: QThreadPool with custom runnable workers
- **Configuration**: QSettings for persistent preferences

### 10.2 Module Structure
```
src/
├── config.py              # Application configuration
├── storage/
│   ├── models.py          # Data models (Prompt, TestCase)
│   └── storage.py         # File storage operations
├── llm/
│   ├── llm_utils_adapter.py   # LLM provider abstraction
│   ├── llm_utils_litellm.py   # LiteLLM integration
│   ├── llm_utils_llmcmd.py    # llm-cmd integration
│   └── special_prompts.py     # Optimization prompt patterns
├── modules/
│   ├── prompt_catalog/        # Prompts Catalog module
│   ├── llm_playground/        # LLM Playground module
│   ├── test_set_manager/      # Test Set Manager module
│   └── eval_playground/       # Eval Playground module
└── utils/                     # Shared utilities
```

### 10.3 Asynchronous Operations
- LLM requests execute in background threads
- Progress indication with cancellation support
- Non-blocking UI during long-running operations

---

## 11. Acceptance Criteria

### 11.1 Definition of Done

A feature is considered complete when:
- [ ] Feature works for the happy path (primary use case functions correctly)
- [ ] Basic error handling prevents crashes on common failure modes
- [ ] Edge cases documented for future iteration

### 11.2 Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Quality regression detection | Identify output degradation | Both similarity scores AND LLM grader feedback flag regressions |
| Evaluation turnaround | < 5 minutes for typical test set | Time from "Run Evaluation" to results displayed |
| Prompt iteration speed | Immediate feedback | Playground response visible within LLM latency + 1s |

### 11.3 MVP Feature Priorities

| ID | Feature | Priority | Status |
|----|---------|----------|--------|
| FR-001 | Prompt CRUD with categorization | Must Have | Implemented |
| FR-002 | LLM Playground with model selection | Must Have | Implemented |
| FR-003 | Template variables ({{var}}) | Must Have | Implemented |
| FR-004 | Test set creation and baseline generation | Must Have | Implemented |
| FR-005 | Comparative evaluation with metrics | Must Have | Implemented |
| FR-006 | Prompt optimization (TAG/PIC/LIFE, Critique & Refine) | Should Have | Implemented |
| FR-007 | Evaluation report export | Should Have | Implemented |
| FR-008 | Multi-provider support (llm-cmd, litellm) | Should Have | Implemented |
