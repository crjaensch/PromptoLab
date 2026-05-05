# GEPA Integration Design for PromptoLab

## 1. Executive Summary

This document describes the systematic integration of [GEPA (Genetic-Pareto)](https://github.com/gepa-ai/gepa) into PromptoLab as a third prompt optimization method alongside the existing **Pattern-based Improve** (TAG/PIC/LIFE) and **Critique & Refine** methods.

GEPA brings **data-driven, metric-guided** prompt optimization to PromptoLab. Unlike the existing methods that use heuristic rewriting or generic critique, GEPA uses actual test cases and their execution results to iteratively evolve better prompts through LLM-based reflection and Pareto-efficient evolutionary search.

### Design Decisions

| Decision | Choice |
|----------|--------|
| Dependency | Use `gepa` library directly (`pip install gepa`) |
| Integration scope | Both playgrounds + standalone mode in LLM Playground |
| Scoring metric | User-selectable (LLM Grade, Cosine Similarity, or Combined) |
| Optimization target | Whichever prompt is active (system prompt if checkbox checked, else user prompt) |

---

## 2. GEPA Methodology Overview

### Core Algorithm

GEPA's optimization loop:

1. **Select** — Pick a candidate from the Pareto frontier (candidates excelling on different task subsets)
2. **Execute** — Run candidate on a minibatch, capturing full execution traces
3. **Reflect** — An LLM reads execution traces (outputs, errors, reasoning) to diagnose *why* a candidate failed
4. **Mutate** — Generate an improved candidate informed by accumulated lessons from all ancestors
5. **Accept** — Add to pool if improved, update the Pareto front

### Key Concept: Actionable Side Information (ASI)

GEPA's differentiator is ASI — diagnostic feedback from evaluators that serves as the text-optimization analogue of a gradient. Instead of collapsing execution traces into a single scalar reward, GEPA feeds full traces to a reflection LLM that can diagnose failures and propose targeted fixes.

### Relevant GEPA APIs

```python
# API 1: gepa.optimize() — for system prompt optimization with train/val sets
result = gepa.optimize(
    seed_candidate={"system_prompt": "You are a helpful assistant..."},
    trainset=trainset,
    valset=valset,
    task_lm="openai/gpt-4.1-mini",
    max_metric_calls=150,
    reflection_lm="openai/gpt-5",
)

# API 2: gepa.optimize_anything() — for general text optimization
import gepa.optimize_anything as oa
result = optimize_anything(
    seed_candidate="<initial text>",
    evaluator=my_evaluator_fn,
    objective="Describe what to optimize for.",
    config=GEPAConfig(engine=EngineConfig(max_metric_calls=100)),
)
```

---

## 3. Current PromptoLab Architecture

### Existing Prompt Optimization Methods

| Method | Location | Mechanism | Requires Test Data |
|--------|----------|-----------|-------------------|
| Improve Prompt (TAG/PIC/LIFE) | LLM Playground | Single-shot pattern-based LLM rewrite | No |
| Critique & Refine | LLM Playground | Iterative critique → refine cycles | No |
| **GEPA (new)** | Both Playgrounds | Data-driven evolutionary search | Yes (Eval) / No (Standalone) |

### Key Components

- **`LLMPlaygroundWidget`** (`src/modules/llm_playground/llm_playground.py`)
  - System prompt + user prompt inputs
  - Parameters panel with model selection, optimization options
  - Output area with "Save as New Prompt" button

- **`EvaluationWidget`** (`src/modules/eval_playground/evaluation_widget.py`)
  - Test set selector + model selector
  - "New System Prompt" input field
  - Results table with per-case grades
  - Uses `OutputAnalyzer` for cosine similarity + LLM grading

- **`CritiqueNRefineWorker`** (`src/modules/llm_playground/critique_n_refine.py`)
  - QObject with `finished`/`progress`/`error`/`cancelled` signals
  - Iterative LLM-based critique and refinement
  - **Pattern to follow for GEPA workers**

- **`LLMWorker`** (`src/llm/llm_utils_adapter.py`)
  - Runs LLM requests via litellm or llm-cmd
  - Thread-pool based execution via `ThreadManager`

- **`OutputAnalyzer`** (`src/modules/eval_playground/output_analyzer.py`)
  - Cosine similarity via embeddings
  - LLM grading on -2 to +2 scale
  - Async analysis via `AsyncAnalyzer`

---

## 4. Integration Architecture

### 4.1 New Files

```
src/
  llm/
    gepa_adapter.py              # PromptoLabAdapter: bridges PromptoLab ↔ GEPA
  modules/
    llm_playground/
      gepa_optimize_worker.py    # GEPAOptimizeAnythingWorker for standalone mode
      gepa_playground_config.py  # Config dialog for LLM Playground GEPA options
    eval_playground/
      gepa_eval_worker.py        # GEPAEvalWorker for test-set-driven optimization
      gepa_eval_config.py        # Config dialog for Eval Playground GEPA options
```

### 4.2 Modified Files

| File | Changes |
|------|---------|
| `requirements.txt` | Add `gepa` dependency |
| `llm_playground.py` | Add "3. GEPA Optimize" section in Parameters panel |
| `evaluation_widget.py` | Add "Optimize with GEPA" button alongside "Run Evaluation" |
| `main_window.py` | Wire test_set_storage to LLM Playground for test set access |
| `special_prompts.py` | (No changes — GEPA uses its own reflection prompts) |

### 4.3 Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                      MainWindow                          │
├──────────────┬──────────────┬───────────┬───────────────┤
│ Prompt       │ LLM          │ Test Set  │ Eval          │
│ Catalog      │ Playground   │ Manager   │ Playground    │
│              │              │           │               │
│              │ ┌──────────┐ │           │ ┌───────────┐ │
│              │ │ Improve  │ │           │ │ Run Eval  │ │
│              │ │ (Patterns)│ │           │ ├───────────┤ │
│              │ ├──────────┤ │           │ │ Optimize  │ │
│              │ │ Critique │ │           │ │ with GEPA │ │
│              │ │ & Refine │ │           │ └─────┬─────┘ │
│              │ ├──────────┤ │           │       │       │
│              │ │ GEPA     │ │           │       ▼       │
│              │ │ Optimize │ │           │ GEPAEvalWorker│
│              │ └────┬─────┘ │           │       │       │
│              │      │       │           │       ▼       │
│              │      ▼       │           │ PromptoLab    │
│              │ GEPAOptimize │           │ Adapter       │
│              │ AnythingWrkr │           │       │       │
│              │      │       │           │       ▼       │
│              │      ▼       │           │ gepa.optimize │
│              │ gepa.optimize│           │               │
│              │ _anything()  │           │               │
└──────────────┴──────┬───────┴───────────┴───────┬───────┘
                      │                           │
                      ▼                           ▼
              ┌───────────────┐          ┌────────────────┐
              │  LLMWorker    │          │ OutputAnalyzer  │
              │  (litellm)    │          │ (scoring)       │
              └───────────────┘          └────────────────┘
```

---

## 5. Detailed Component Design

### 5.1 `PromptoLabAdapter` (`src/llm/gepa_adapter.py`)

A custom GEPA adapter that bridges PromptoLab's evaluation infrastructure to GEPA's `GEPAAdapter` protocol.

```python
"""
PromptoLabAdapter — Bridges PromptoLab's LLM and evaluation 
infrastructure to GEPA's GEPAAdapter protocol.
"""
import gepa
from gepa.core.adapter import GEPAAdapter, EvaluationBatch
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

@dataclass
class PromptoLabTrajectory:
    """Captures execution trace for a single test case."""
    input_text: str
    baseline_output: str
    current_output: str
    similarity_score: float
    llm_grade: str
    llm_feedback: str

class PromptoLabAdapter:
    """
    Implements GEPAAdapter protocol for PromptoLab.
    
    - evaluate(): Runs candidate system prompt on test cases using LLMWorker,
      then scores via the user-selected metric.
    - make_reflective_dataset(): Packages execution traces into GEPA's 
      reflective dataset format for the reflection LLM.
    """
    
    def __init__(self, task_lm: str, metric_type: str = "llm_grade",
                 llm_api_fn=None, embed_fn=None, grade_fn=None):
        self.task_lm = task_lm
        self.metric_type = metric_type  # "llm_grade", "cosine_similarity", "combined"
        self.llm_api_fn = llm_api_fn    # Sync wrapper around LLMWorker
        self.embed_fn = embed_fn        # Sync wrapper around EmbedWorker
        self.grade_fn = grade_fn        # Sync wrapper around LLM grading
    
    def evaluate(self, batch, candidate, capture_traces=False):
        """
        Run the candidate system prompt on each test case in the batch.
        
        - batch: list of TestCase-like dicts with input_text & baseline_output
        - candidate: {"system_prompt": "..."} 
        - Returns: EvaluationBatch with scores and optional trajectories
        """
        outputs = []
        scores = []
        trajectories = []
        
        system_prompt = candidate.get("system_prompt", "")
        
        for example in batch:
            # Run LLM with candidate system prompt
            current_output = self.llm_api_fn(
                model=self.task_lm,
                user_prompt=example["input_text"],
                system_prompt=system_prompt
            )
            outputs.append(current_output)
            
            # Score based on metric_type
            score = self._compute_score(
                example["input_text"],
                example.get("baseline_output", ""),
                current_output
            )
            scores.append(score)
            
            if capture_traces:
                trajectories.append(PromptoLabTrajectory(
                    input_text=example["input_text"],
                    baseline_output=example.get("baseline_output", ""),
                    current_output=current_output,
                    similarity_score=score,
                    llm_grade="",  # Populated during scoring
                    llm_feedback=""
                ))
        
        return EvaluationBatch(
            outputs=outputs,
            scores=scores,
            trajectories=trajectories if capture_traces else None
        )
    
    def make_reflective_dataset(self, candidate, eval_batch, components_to_update):
        """
        Build reflective dataset from execution traces.
        
        Returns per-component list of dicts with:
        - Inputs: the test case input
        - Generated Outputs: what the candidate produced
        - Feedback: baseline comparison + score + LLM feedback
        """
        dataset = {}
        for component in components_to_update:
            records = []
            for i, traj in enumerate(eval_batch.trajectories):
                records.append({
                    "Inputs": {"user_prompt": traj.input_text},
                    "Generated Outputs": traj.current_output,
                    "Expected Output": traj.baseline_output,
                    "Score": eval_batch.scores[i],
                    "Feedback": (
                        f"Score: {eval_batch.scores[i]:.2f}. "
                        f"Expected output: {traj.baseline_output[:200]}... "
                        f"Got: {traj.current_output[:200]}..."
                    )
                })
            dataset[component] = records
        return dataset
    
    def _compute_score(self, input_text, baseline, current):
        """Compute score based on the selected metric type."""
        if self.metric_type == "cosine_similarity":
            return self._cosine_score(baseline, current)
        elif self.metric_type == "llm_grade":
            return self._llm_grade_score(input_text, baseline, current)
        else:  # combined
            cos = self._cosine_score(baseline, current)
            grade = self._llm_grade_score(input_text, baseline, current)
            return 0.5 * cos + 0.5 * ((grade + 2) / 4)  # Normalize grade to [0,1]
```

### 5.2 `GEPAEvalWorker` (`src/modules/eval_playground/gepa_eval_worker.py`)

Worker for the Eval Playground integration. Runs GEPA optimization using test sets.

```python
"""
GEPAEvalWorker — Runs gepa.optimize() against a PromptoLab test set.
Follows the same QObject signal pattern as CritiqueNRefineWorker.
"""
from PySide6.QtCore import Signal, QObject

class GEPAEvalWorker(QObject):
    finished = Signal(str)      # Emits the optimized system prompt
    progress = Signal(str)      # Emits progress updates  
    error = Signal(str)         # Emits error messages
    cancelled = Signal()        # Emits when cancelled
    score_updated = Signal(float)  # Emits current best score
    
    def __init__(self, seed_prompt, test_cases, task_lm, reflection_lm,
                 max_metric_calls, metric_type, llm_api_fn, embed_fn, grade_fn):
        super().__init__()
        self.seed_prompt = seed_prompt
        self.test_cases = test_cases
        self.task_lm = task_lm
        self.reflection_lm = reflection_lm
        self.max_metric_calls = max_metric_calls
        self.metric_type = metric_type
        self.llm_api_fn = llm_api_fn
        self.embed_fn = embed_fn
        self.grade_fn = grade_fn
        self.cancelled_flag = False
    
    def run(self):
        """Execute GEPA optimization in a background thread."""
        try:
            import gepa
            from src.llm.gepa_adapter import PromptoLabAdapter
            
            # Build adapter
            adapter = PromptoLabAdapter(
                task_lm=self.task_lm,
                metric_type=self.metric_type,
                llm_api_fn=self.llm_api_fn,
                embed_fn=self.embed_fn,
                grade_fn=self.grade_fn
            )
            
            # Convert TestCases to GEPA format
            trainset, valset = self._split_test_cases()
            
            # Seed candidate
            seed_candidate = {"system_prompt": self.seed_prompt}
            
            self.progress.emit("Starting GEPA optimization...")
            
            # Run optimization
            result = gepa.optimize(
                seed_candidate=seed_candidate,
                trainset=trainset,
                valset=valset,
                task_lm=self.task_lm,
                reflection_lm=self.reflection_lm,
                max_metric_calls=self.max_metric_calls,
                adapter=adapter,
            )
            
            if self.cancelled_flag:
                self.cancelled.emit()
                return
            
            optimized_prompt = result.best_candidate["system_prompt"]
            best_score = result.best_score
            
            # Format result
            output = self._format_result(optimized_prompt, best_score)
            self.finished.emit(output)
            
        except Exception as e:
            self.error.emit(str(e))
    
    def _split_test_cases(self):
        """Split test cases into train/val sets (80/20)."""
        split = max(1, int(len(self.test_cases) * 0.8))
        train = [{"input_text": tc.input_text, "baseline_output": tc.baseline_output}
                 for tc in self.test_cases[:split]]
        val = [{"input_text": tc.input_text, "baseline_output": tc.baseline_output}
               for tc in self.test_cases[split:]]
        if not val:  # If too few cases, use same as train
            val = train
        return train, val
    
    def _format_result(self, optimized_prompt, best_score):
        return (
            "# GEPA Prompt Optimization Results\n\n"
            f"**Best Score:** {best_score:.4f}\n\n"
            "## Optimized System Prompt\n\n"
            f"{optimized_prompt}"
        )
    
    def cancel(self):
        self.cancelled_flag = True
```

### 5.3 `GEPAOptimizeAnythingWorker` (`src/modules/llm_playground/gepa_optimize_worker.py`)

Worker for the LLM Playground standalone mode using `optimize_anything`.

```python
"""
GEPAOptimizeAnythingWorker — Uses gepa.optimize_anything() for 
prompt optimization without requiring test data.
The user provides an objective description instead.
"""
from PySide6.QtCore import Signal, QObject

class GEPAOptimizeAnythingWorker(QObject):
    finished = Signal(str)
    progress = Signal(str)
    error = Signal(str)
    cancelled = Signal()
    
    def __init__(self, seed_prompt, objective, max_metric_calls,
                 task_lm, reflection_lm):
        super().__init__()
        self.seed_prompt = seed_prompt
        self.objective = objective
        self.max_metric_calls = max_metric_calls
        self.task_lm = task_lm
        self.reflection_lm = reflection_lm
        self.cancelled_flag = False
    
    def run(self):
        """Execute optimize_anything in a background thread."""
        try:
            import gepa.optimize_anything as oa
            from gepa.optimize_anything import (
                optimize_anything, GEPAConfig, EngineConfig
            )
            
            self.progress.emit("Starting GEPA optimize_anything...")
            
            def evaluator(candidate: str) -> float:
                """
                Uses the reflection LLM itself to score the candidate 
                prompt quality against the objective.
                """
                # Use LLM to evaluate the candidate against the objective
                eval_prompt = (
                    f"Rate this prompt on a scale of 0.0 to 1.0 based on "
                    f"how well it achieves this objective: {self.objective}\n\n"
                    f"Prompt to evaluate:\n{candidate}\n\n"
                    f"Respond with ONLY a decimal number between 0.0 and 1.0."
                )
                # This will use the configured LLM API
                result = self._run_llm_sync(eval_prompt)
                try:
                    score = float(result.strip())
                    return max(0.0, min(1.0, score))
                except ValueError:
                    return 0.5
            
            result = optimize_anything(
                seed_candidate=self.seed_prompt,
                evaluator=evaluator,
                objective=self.objective,
                config=GEPAConfig(
                    engine=EngineConfig(max_metric_calls=self.max_metric_calls)
                ),
            )
            
            if self.cancelled_flag:
                self.cancelled.emit()
                return
            
            output = (
                "# GEPA Optimize Anything Results\n\n"
                f"**Objective:** {self.objective}\n\n"
                "## Optimized Prompt\n\n"
                f"{result.best_candidate}"
            )
            self.finished.emit(output)
            
        except Exception as e:
            self.error.emit(str(e))
    
    def cancel(self):
        self.cancelled_flag = True
```

### 5.4 Config Dialogs

#### `GEPAEvalConfigDialog` (Eval Playground)

```python
"""Config dialog for GEPA optimization in the Eval Playground."""

class GEPAEvalConfigDialog(QDialog):
    """
    Fields:
    - Reflection LM: Model selector (defaults to same as task LM)
    - Max Metric Calls: SpinBox (range 20-500, default 100)
    - Metric Type: ComboBox ["LLM Grade", "Cosine Similarity", "Combined"]
    - Description text explaining GEPA methodology
    - Start / Cancel buttons
    """
```

#### `GEPAPlaygroundConfigDialog` (LLM Playground)

```python
"""Config dialog for GEPA optimization in the LLM Playground."""

class GEPAPlaygroundConfigDialog(QDialog):
    """
    Two modes via tab widget:
    
    Tab 1 — "With Test Set":
    - Test Set: ComboBox (loads available test sets from TestSetStorage)
    - Reflection LM: Model selector
    - Max Metric Calls: SpinBox
    - Metric Type: ComboBox
    
    Tab 2 — "Standalone":
    - Objective: TextEdit (user describes what to optimize for)
    - Reflection LM: Model selector  
    - Max Metric Calls: SpinBox
    """
```

---

## 6. UI Integration Details

### 6.1 Optimization Target Logic (LLM Playground)

When the user clicks "GEPA Optimize" in the LLM Playground, the system determines which prompt to optimize based on UI state:

```python
def _get_optimization_target(self):
    """Determine which prompt field to optimize."""
    if self.system_prompt_checkbox.isChecked() and self.system_prompt.isVisible():
        system_text = self.system_prompt.toPlainText().strip()
        if system_text:
            return "system_prompt", system_text
    # Fall back to user prompt
    return "user_prompt", self.user_prompt.toPlainText().strip()
```

**Behavior:**
- If system prompt checkbox is **checked** and has content → GEPA optimizes the **system prompt** (user prompt becomes test input)
- If system prompt is **unchecked/empty** → GEPA optimizes the **user prompt**
- The GEPA candidate dict key matches the target: `{"system_prompt": "..."}` or `{"user_prompt": "..."}`
- On completion, the optimized text is placed back into the **same field** it was read from

In the **Eval Playground**, the target is always the system prompt (matching the existing "New System Prompt" input field).

### 6.2 LLM Playground — Parameters Panel

Add a third section below "2. Critique and Refine Prompt":

```
Prompt Optimization Options:
├── 1. Improve Prompt using Pattern
│   └── [Improve Prompt] Pattern: [TAG ▼]
├── 2. Critique and Refine Prompt
│   └── [Refine Prompt]
└── 3. GEPA Optimize                          ← NEW
    └── [GEPA Optimize]
```

The "GEPA Optimize" button:
- Opens `GEPAPlaygroundConfigDialog`
- User selects mode (test-set or standalone) and configures parameters
- Runs optimization in background with progress updates
- Result appears in output area
- "Save as New Prompt" button becomes enabled

#### Code Changes to `llm_playground.py`

In `setup_ui()`, after the Critique & Refine section (~line 335):

```python
# 3. GEPA Optimize section
params_content_layout.addSpacing(5)
gepa_label = QLabel("3. GEPA Optimize")
params_content_layout.addWidget(gepa_label)

gepa_controls = QHBoxLayout()
gepa_controls.setSpacing(0)

gepa_btn = QPushButton("GEPA Optimize")
gepa_btn.setMinimumHeight(30)
gepa_btn.setFixedWidth(120)
gepa_btn.setToolTip("Optimize prompt using GEPA evolutionary search")
gepa_btn.clicked.connect(self.gepa_optimize_prompt)
gepa_controls.addWidget(gepa_btn)
gepa_controls.addStretch()

params_content_layout.addLayout(gepa_controls)
```

New method `gepa_optimize_prompt()` follows the same pattern as `critique_and_refine_prompt()`.

### 6.3 Eval Playground — Button Bar

Add "Optimize with GEPA" button next to "Run Evaluation":

```
[Progress Bar                    ] [Run Evaluation] [Optimize with GEPA] [Export Results]
```

The button:
- Opens `GEPAEvalConfigDialog` 
- Runs `GEPAEvalWorker` with the current test set
- Progress bar shows iteration count and current best score
- On completion: 
  - Optimized prompt is placed in the "New System Prompt" input
  - User can then "Run Evaluation" to verify the improvement
  - Status bar shows "GEPA optimization completed! Best score: X.XX"

#### Code Changes to `evaluation_widget.py`

In `setup_ui()`, after the export button (~line 315):

```python
# Optimize with GEPA button
self.gepa_button = QPushButton("Optimize with GEPA")
self.gepa_button.clicked.connect(self.optimize_with_gepa)
self.gepa_button.setStyleSheet("""
    QPushButton {
        padding: 5px 15px;
        background: #9b59b6;
        color: white;
        border: none;
        border-radius: 2px;
    }
    QPushButton:hover { background: #8e44ad; }
    QPushButton:disabled { background: #95a5a6; }
""")
bottom_layout.addWidget(self.gepa_button)
```

### 6.4 MainWindow Wiring

Pass `test_set_storage` to `LLMPlaygroundWidget` so it can load test sets for the GEPA test-set mode:

```python
# In MainWindow.setup_ui():
self.llm_playground = LLMPlaygroundWidget(self.settings, self.test_set_storage)
```

---

## 7. Threading & Async Design

### Synchronous Wrappers for GEPA

GEPA's `optimize()` and `optimize_anything()` are synchronous, blocking calls. They expect the adapter's `evaluate()` method to be synchronous too. However, PromptoLab's `LLMWorker` is async (signal-based).

**Solution:** Create synchronous wrapper functions that block until the LLM call completes. These run inside the GEPA optimization thread (not the UI thread).

```python
# In gepa_adapter.py

import threading

def make_sync_llm_fn():
    """Create a synchronous LLM call function for use in GEPA threads."""
    def sync_llm_call(model, user_prompt, system_prompt=None):
        """Blocking LLM call using litellm directly."""
        from src.llm import llm_utils_litellm
        from src.config import config
        
        if config.llm_api == 'llm-cmd':
            from src.llm import llm_utils_llmcmd
            return llm_utils_llmcmd.run_llm(model, user_prompt, system_prompt, {})
        else:
            return llm_utils_litellm.run_llm(model, user_prompt, system_prompt, {})
    
    return sync_llm_call
```

### Worker Execution

Both `GEPAEvalWorker` and `GEPAOptimizeAnythingWorker` will:

1. Be created on the UI thread
2. Have their `run()` method executed via `ThreadManager.instance().start_runnable()` (same pattern as existing workers)
3. Emit signals back to the UI thread for progress/completion/error
4. Support cancellation via a flag checked between GEPA iterations

---

## 8. Data Flow Diagrams

### 8.1 Eval Playground GEPA Flow

```
User clicks "Optimize with GEPA"
        │
        ▼
GEPAEvalConfigDialog shown
   - reflection_lm, max_metric_calls, metric_type
        │
        ▼
GEPAEvalWorker created with:
   - seed_prompt = system_prompt_input.toPlainText()
   - test_cases = current_test_set.cases
   - task_lm = model_combo.currentText()
   - config from dialog
        │
        ▼
Worker.run() [in background thread]
   │
   ├── Build PromptoLabAdapter
   ├── Convert TestCases → trainset/valset
   ├── Call gepa.optimize()
   │      │
   │      ├── GEPA calls adapter.evaluate(batch, candidate)
   │      │      ├── For each test case:
   │      │      │   ├── Run LLM with candidate system prompt
   │      │      │   └── Score (cosine sim / LLM grade / combined)
   │      │      └── Return EvaluationBatch
   │      │
   │      ├── GEPA calls adapter.make_reflective_dataset()
   │      │      └── Package traces for reflection LLM
   │      │
   │      └── GEPA proposes mutations, evaluates, accepts/rejects
   │
   └── Emit finished(optimized_prompt)
        │
        ▼
UI updates:
   - system_prompt_input.setPlainText(optimized_prompt)
   - Status: "GEPA optimization completed!"
   - User can now click "Run Evaluation" to verify
```

### 8.2 LLM Playground Standalone GEPA Flow

```
User clicks "GEPA Optimize"
        │
        ▼
GEPAPlaygroundConfigDialog shown
   - Tab "Standalone": objective, reflection_lm, max_metric_calls
        │
        ▼
GEPAOptimizeAnythingWorker created with:
   - seed_prompt = user_prompt (+ system_prompt if visible)
   - objective from dialog
   - task_lm = model_combo.currentText()
        │
        ▼
Worker.run() [in background thread]
   │
   ├── Call gepa.optimize_anything()
   │      ├── GEPA calls evaluator(candidate_text)
   │      │      └── LLM-based scoring against objective
   │      └── GEPA reflects, mutates, selects
   │
   └── Emit finished(optimized_prompt)
        │
        ▼
UI updates:
   - playground_output.setMarkdown(result)
   - save_as_prompt_button.setEnabled(True)
```

---

## 9. Metric Configuration

Users can select from three scoring metrics in the GEPA config dialogs:

### LLM Grade (Default)

Uses the existing grading infrastructure from `OutputAnalyzer`:
- LLM compares current output to baseline
- Returns grade on -2 to +2 scale
- Normalized to [0, 1] for GEPA: `(grade + 2) / 4`

**Pros:** Captures quality nuance, considers semantic meaning  
**Cons:** Expensive (extra LLM call per evaluation), slower

### Cosine Similarity

Uses embedding-based similarity from `OutputAnalyzer`:
- Embeds both baseline and current output
- Returns cosine similarity in [0, 1]

**Pros:** Fast, cheap, deterministic  
**Cons:** Only measures similarity to baseline (not "better than baseline")

### Combined

Weighted average of both metrics:
```python
score = 0.5 * cosine_similarity + 0.5 * normalized_llm_grade
```

**Pros:** Balanced signal  
**Cons:** Most expensive (both embedding + LLM grading calls)

---

## 10. Error Handling & Edge Cases

| Scenario | Handling |
|----------|----------|
| `gepa` not installed | Show helpful error message with install instructions |
| Test set has < 3 cases | Warning dialog; GEPA works with few examples but quality may vary |
| LLM API errors during optimization | GEPA handles per-example failures gracefully (score = 0.0); systemic errors abort |
| User cancels mid-optimization | Set `cancelled_flag`; return best candidate found so far |
| Empty seed prompt | Prompt user to enter a seed system prompt first |
| No baseline outputs in test cases | Disable LLM Grade metric; only allow cosine similarity or standalone mode |
| GEPA timeout / long run | Progress dialog shows iteration count; user can cancel anytime |

---

## 11. Implementation Plan

### Phase 1: Foundation (Priority: High)

1. **Add `gepa` to `requirements.txt`**
2. **Create `src/llm/gepa_adapter.py`**
   - `PromptoLabAdapter` implementing GEPA's adapter protocol
   - Synchronous LLM/embed wrappers for use in GEPA threads
3. **Create config dialogs**
   - `gepa_eval_config.py` for Eval Playground
   - `gepa_playground_config.py` for LLM Playground

### Phase 2: Eval Playground Integration (Priority: High)

4. **Create `src/modules/eval_playground/gepa_eval_worker.py`**
   - `GEPAEvalWorker` with signal-based async execution
5. **Modify `evaluation_widget.py`**
   - Add "Optimize with GEPA" button
   - Add `optimize_with_gepa()` method
   - Wire signals for progress, completion, error

### Phase 3: LLM Playground Integration (Priority: Medium)

6. **Create `src/modules/llm_playground/gepa_optimize_worker.py`**
   - `GEPAOptimizeAnythingWorker` for standalone mode
   - Test-set mode variant (reuses `GEPAEvalWorker`)
7. **Modify `llm_playground.py`**
   - Add "3. GEPA Optimize" section in Parameters panel
   - Add `gepa_optimize_prompt()` method with config dialog
8. **Modify `main_window.py`**
   - Pass `test_set_storage` to `LLMPlaygroundWidget`

### Phase 4: Polish & Testing (Priority: Medium)

9. **Add tests**
   - Unit tests for `PromptoLabAdapter`
   - Integration tests for GEPA workers
   - Mock GEPA calls for CI
10. **UX refinements**
    - Progress messages showing GEPA iteration details
    - Result formatting with optimization history
    - Tooltip help text explaining GEPA

### Estimated Effort

| Phase | Effort |
|-------|--------|
| Phase 1: Foundation | ~4 hours |
| Phase 2: Eval Playground | ~3 hours |
| Phase 3: LLM Playground | ~3 hours |
| Phase 4: Polish & Testing | ~3 hours |
| **Total** | **~13 hours** |

---

## 12. Future Enhancements

- **Optimization History View:** Show the evolution of prompts across GEPA iterations (Pareto front visualization)
- **Multi-objective UI:** Let users define multiple objectives and see the Pareto frontier
- **GEPA Presets:** Save/load GEPA configurations for common optimization patterns
- **Batch Comparison:** Compare GEPA-optimized vs. Critique & Refine vs. Pattern-based results side-by-side
- **DSPy Integration:** For users with DSPy pipelines, expose `dspy.GEPA` as an additional optimization mode
