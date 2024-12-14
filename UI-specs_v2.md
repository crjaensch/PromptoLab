# PromptoLab UI Specification

## 1. Application Structure and Navigation
The PromptoLab UI consists of three main parts, each accessible through a tab control located at the top left of the main window:
- **Prompts Catalog**
- **LLM Playground**
- **Test Set Manager**
- **Eval Playground**

## 2. Global UI Guidelines and Behaviors

### 2.1 Expandable/Collapsible Groups
When implementing UI element groups that support expand/collapse functionality, the following rules apply:
- In the collapsed state, all contents including headers must be hidden, with only the expand/collapse button remaining visible
- The expand/collapse button must be positioned at the top-right of the group area
- The button design must follow these specifications:
  - Square shape with slightly rounded corners (4px radius)
  - Fixed size of 28x28 pixels
  - Light gray background (#f8f8f8)
  - Thin border (#e0e0e0, 1px)
  - Plus/minus symbols using Arial font, 16px, ExtraBold weight
  - Gray text color (#666666) with black (#000000) on hover
  - Background lightens (#f0f0f0) and border darkens (#cccccc) on hover
- When collapsed, the group width should be exactly 44px to accommodate the button + margins
- The transition between states should be animated with a duration of 200ms
- The Parameters panel should default to collapsed state on first launch
- The Prompts panel should default to expanded state on first launch

### 2.2 State Persistence
The application must maintain the following states between user sessions:
- Expand/collapse states for all collapsible groups
- The most recently selected prompt in the Prompts Catalog
- All LLM parameter settings (Temperature, Max Tokens, Stream setting)
- The selected LLM model and its settings
- System Prompt visibility state and content
- Panel expansion states for both Parameters and Prompts panels

### 2.3 Visual Styling Standards
To maintain consistency across the application:
- All text input areas must use 16px padding and a minimum height of 100px for multiline inputs
- Visual borders around main interaction areas must use a light gray color (#CCCCCC) with 1px width
- Spacing between major UI elements must be consistently 16px
- Input fields must have a consistent height of 40px for single-line inputs
- All interactive elements must show hover and focus states with a light gray background (#BBBBBB)
- Text input areas must use a light gray background (#F5F5F5)
- List items must show distinct hover and selection states with the same background color (#BBBBBB)

### 2.4 LLM Parameters and Model Selection
The application provides consistent LLM parameter controls across all relevant interfaces:

#### Model Selection
- Available models are dynamically loaded from the `llm` command-line tool
- Model dropdown appears in both LLM Playground and Eval Playground
- Default model is "gpt-4o-mini" if model list cannot be loaded
- Model list is synchronized between all interfaces using the same model

#### Optional LLM Parameters
The following parameters are optional and synchronized across interfaces:
- **Temperature**: Floating-point value for response randomness
  - Empty option available as default
  - Common values: 0.0, 0.3, 0.5, 0.7, 0.9, 1.0
- **Max Tokens**: Integer value for response length limit
  - Empty option available as default
  - Common values: 512, 1024, 2048, 4096, 8192
- **Top P**: Floating-point value for nucleus sampling
  - Empty option available as default
  - Common values: 0.1, 0.5, 0.7, 0.8, 0.9, 0.95, 1.0

#### Parameter Persistence
- All parameter values are stored in application settings
- Values persist between sessions
- Settings are shared between LLM Playground and Eval Playground
- Empty selections are preserved and passed as None to the LLM

## 3. Prompts Catalog Implementation

### 3.1 Right-Side Group
The collapsible group on the right side must:
- Default to expanded state on first application launch
- Include a search field that filters prompts in real-time as the user types
- Present a prompt selection list where:
  - Titles longer than 32 characters must be truncated with an ellipsis
  - Items must be sorted alphanumerically by title
  - The list must support keyboard navigation
  - Selected items must be visually distinct with a light blue background (#EBF5FF)

### 3.2 Main Interaction Area
The prompt editing area must implement the following behaviors:
- Unsaved changes detection:
  - Modified fields must be visually indicated with a subtle border color change
  - Attempting to switch prompts with unsaved changes must trigger a confirmation dialog
  - The Save button must only be enabled when changes are detected
- The Cancel button must revert all fields to their last saved state
- For prompt templates, the text area must:
  - Highlight placeholder variables (text within double curly braces) in a distinct color
  - Provide autocompletion suggestions for common placeholder variables
  - Support multi-line editing with proper indentation handling

## 4. LLM Playground Implementation

### 4.1 Parameter Controls
The left-side parameter group must:
- Default to collapsed state on first application launch
- Include a model selection dropdown with support for:
  - All models supported by the "llm models" command-line tool
  - Default model: "gpt-4o-mini"
- Implement Temperature control using ComboBox:
  - Empty option as default
  - Predefined values: 0.0, 0.3, 0.5, 0.7, 0.9, 1.0
  - Display empty selection as "undefined"
- Implement Max Tokens control using ComboBox:
  - Empty option as default
  - Predefined values: 512, 1024, 2048, 4096, 8192
  - Display empty selection as "undefined"
- Implement Top P control using ComboBox:
  - Empty option as default
  - Predefined values: 0.1, 0.5, 0.7, 0.8, 0.9, 0.95, 1.0
  - Display empty selection as "undefined"
- All parameter controls must:
  - Maintain state between sessions
  - Share settings with other interfaces
  - Support keyboard navigation
  - Show clear visual indication of selected value

### 4.2 Parameters Panel
The collapsible Parameters panel must:
- Default to collapsed state
- When expanded, show:
  - Model selection dropdown with dynamically loaded models
  - Optional parameter controls:
    - Temperature with empty default
    - Max Tokens with empty default
    - Top P with empty default
  - System prompt toggle and input area
- Maintain all settings in application state
- Share settings with Eval Playground

#### System Prompt Section
- A checkbox controls complete visibility of the System Prompt text area
- The text area must animate smoothly when shown/hidden
- When hidden, the space must collapse to prevent empty gaps in the layout
- The system prompt must use the ExpandableTextWidget component for dynamic resizing
- Default minimum height should be 120px
- Must include placeholder text: "Enter an optional system prompt..."

#### User Prompt Section
- Must reflect the Current Prompt from the Prompts Catalog when specified
- Must maintain a separate history of edits from the original prompt
- Must provide a "Reset to Original" option when modified from a Current Prompt
- Default minimum height should be 180px
- Must include placeholder text: "Enter your prompt here..."

#### Layout Management
- Implement QSplitter components for flexible sizing of input/output areas
- Default split ratios:
  - Playground: 50/50 split (1000:1000 ratio)
  - When output is expanded: 200:1800 ratio
  - Prompts Catalog: 40/60 split for system/user prompts (400:600)
  - When system prompt is expanded: 1800:200 ratio

#### Response Handling
The response area must:
- Use the ExpandableTextWidget component for dynamic resizing
- Render markdown formatting in real-time using a standard markdown parser
- When streaming is enabled:
  - Show a typing indicator during response generation
  - Render markdown elements as they complete (not character by character)
  - Provide a "Stop Generation" button during streaming
- Display character and token counts below the response area
- Include a copy button in the top-right corner
- Support syntax highlighting for code blocks
- Maintain scroll position when content updates

#### Button Layout
- Center-align action buttons with proper spacing
- Group "Run" and "Improve Prompt" buttons side by side
- Maintain consistent 16px spacing between button groups

#### Optimization Feature
When the Optimize button is clicked:
- Show a loading spinner in the button
- Disable other controls during optimization
- Present the improved prompt in the Response area with:
  - A clear "Improved User Prompt" markdown heading
  - Visual differentiation between the original and improved sections
  - An "Apply Optimization" button to replace the current prompt with the improved version

## 5. Error Handling and Feedback
The application must provide clear feedback for:
- Network connectivity issues
- Invalid parameter combinations
- Rate limiting or quota exhaustion
- Unsuccessful prompt optimization attempts
- Unsaved changes when navigating away

These error states must:
- Use non-intrusive toast notifications for temporary issues
- Show inline error messages for field-specific problems
- Provide actionable feedback when possible
- Maintain accessibility with proper ARIA attributes

## 6. Keyboard Navigation
The application must support efficient keyboard navigation:
- Tab order must follow a logical flow through the interface
- Collapsible groups must be togglable with Enter/Space
- Ctrl+S must save the current prompt when editing
- Esc must cancel the current operation or close dialogs
- Arrow keys must navigate through the prompt selection list

## 7. Eval Playground Implementation

### 7.1 Test Set Management
The Test Set Manager must:
- Provide a dedicated interface for creating and managing test sets
- Include fields for:
  - Test Set Name (required)
  - System Prompt (optional, using ExpandableTextWidget)
  - Test Cases table with columns:
    - User Prompt
    - Baseline Output
- Support adding, editing, and removing test cases
- Validate inputs before saving
- Maintain persistence of test sets between sessions

### 7.2 Control Panel
Must include:
- Test Set selection dropdown
- Model selection dropdown (dynamically populated)
- Optional LLM parameter controls:
  - Temperature (empty default)
  - Max Tokens (empty default)
  - Top P (empty default)
- System prompt input area
- Run evaluation button

#### Test Set Selection Area
- Dropdown for selecting test sets
- Model selection dropdown with support for all models supported by "llm models"
- System Prompt input using ExpandableTextWidget
  - Default collapsed height: 35px
  - Expanded height: 200px
  - Placeholder text: "Enter the new system prompt to evaluate..."

#### Results Table
- Columns:
  - User Prompt
  - Baseline Output
  - Current Output
  - Semantic Similarity (numeric, 2 decimal places)
  - LLM Grade (A-F scale)
- Features:
  - Auto-adjusting row heights for content
  - Horizontal scrolling for long content
  - Selection highlighting
  - Column width optimization:
    - Fixed width for numeric columns (Similarity: 100px, Grade: 80px)
    - Flexible width for text columns

#### Analysis Panel
- Collapsible panel with toggle button (▼/▶)
- Tab interface with:
  - Semantic Analysis tab
    - Shows detailed similarity breakdown
    - Highlights key differences
  - LLM Feedback tab
    - Shows structured feedback
    - Includes grade explanation
- Read-only text areas for analysis display

### 7.3 Evaluation Process
The interface must support:
- Progress indication during evaluation
  - Progress bar showing current/total test cases
  - Disable run button during evaluation
- Real-time updates
  - Update table as each test case completes
  - Show analysis for selected test case
- Error handling
  - Clear error messages for LLM failures
  - Proper recovery from network issues
  - Option to retry failed evaluations

### 7.4 Visual Feedback
- Color-coding for grades (optional future enhancement)
- Visual indicators for similarity scores
- Clear differentiation between baseline and current outputs
- Loading states during analysis
- Error states for failed evaluations

### 7.5 Interaction Patterns
- Single-click row selection for viewing analysis
- Double-click cell for copying content
- Keyboard navigation support
- Tab order:
  1. Test Set dropdown
  2. Model dropdown
  3. System Prompt
  4. Run button
  5. Results table
  6. Analysis tabs

### 7.6 State Management
Must persist:
- Selected test set
- Selected model
- System prompt content
- Analysis panel expansion state
- Table column widths
- Selected row index

### 7.7 Performance Considerations
- Efficient handling of large test sets
- Smooth scrolling in results table
- Responsive analysis updates
- Proper cleanup of resources
- Memory management for large outputs

## 8. Test Set Manager Implementation

### 8.1 Interface Layout
The test set manager interface consists of:
- Test set information section at the top
- System prompt section
- Test cases table
- Action buttons at the bottom

### 8.2 Test Set Information
- Test set name input field
- System prompt input using ExpandableTextWidget
  - Initial height of 35px (2 lines)
  - Expandable for longer prompts
  - Placeholder text: "Enter system prompt here..."

### 8.3 Test Cases Table
- Two-column layout:
  - User Prompt
  - Baseline Output
- Features:
  - Horizontal header with column labels
  - Automatic column width adjustment
  - Vertical scrolling for many test cases
  - Selection highlighting

### 8.4 Action Buttons
Horizontally arranged buttons for:
- Add Test Case
- Remove Selected
- Generate Baseline
- Save Test Set
- Load Test Set

### 8.5 Baseline Generation
- Uses the same LLM parameters as playground
- Shows progress dialog during generation
- Supports cancellation
- Provides error handling per test case
- Uses shared settings for:
  - Selected model
  - Temperature
  - Max tokens
  - Top P

### 8.6 State Management
Must persist:
- Test set name
- System prompt
- All test cases
- Table column widths
- Selected row index