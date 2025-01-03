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

### 3.3 Prompt Templates
The application must support parameterized prompts through a template system:
- Template Variables:
  - Variables are defined using double curly braces: {{variable-name}}
  - Variables must be visually distinct within the prompt text
  - The system should detect and parse variables automatically
- Variables Table:
  - Display a table of all detected variables when a template is active
  - Each variable should have:
    - Name (derived from the template)
    - Value field for user input
    - Clear indication if the value is required
  - The table should update dynamically as variables are added or removed
  - Support for multiple occurrences of the same variable
- Variable Persistence:
  - Clear values when switching to a different prompt
  - Provide a way to reset all values to empty state

### 3.4 Template Interaction
The template system must provide:
- Intuitive variable creation through typing {{a-variable-name}}
- Clear visual feedback when variables are recognized
- Easy navigation between variable input fields
- Validation of required variables before execution
- Error handling for:
  - Missing required values

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
The system prompt functionality must:
- Be consistently implemented across all interfaces
- Support both collapsed and expanded states
  - Collapsed state should be compact to save screen space
  - Expanded state should provide comfortable editing space
- Maintain visual consistency with other text input areas
- Provide clear visual feedback for state changes
- Include appropriate placeholder text based on context:
  - Test Sets: Guide users on system prompt purpose
  - Evaluation: Indicate the evaluation context
  - Playground: Clarify the optional nature
- Preserve user's preferred state between sessions

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
When the Improve Prompt button is clicked:
- Show a loading spinner in the button
- Disable other controls during optimization
- Present the improved prompt in the Response area with:
  - A clear "Improved User Prompt" markdown heading
  - Visual differentiation between the original and improved sections

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

### 7.1 Core Functionality
The evaluation interface must provide:
- Test set selection and management
- Model selection with dynamic model list
- System prompt modification capability
- Comparative evaluation of test cases
- Detailed analysis of results

### 7.2 Main Interface Elements
The interface must include:
- Selection controls for test set and model
- System prompt input that can be expanded when needed
- Results display showing:
  - Original test cases
  - Generated responses
  - Quality metrics
- Analysis area for detailed feedback

### 7.3 Results Presentation
The results must show:
- User prompts from test cases
- Original baseline outputs
- New generated outputs
- Quality metrics:
  - Semantic similarity scores
  - LLM evaluation grades
- Clear visual distinction between different result types

### 7.4 Evaluation Process
The system must:
- Show clear progress during evaluation
- Process test cases sequentially
- Update results in real-time
- Provide error handling for:
  - Failed evaluations
  - Network issues
  - Invalid configurations

### 7.5 Analysis Features
For each evaluated test case:
- Compare original and new outputs
- Calculate similarity metrics
- Provide LLM grader generated structured feedback
- Allow detailed inspection of differences

### 7.6 State Management
The interface must maintain:
- Selected test set
- Chosen model
- Modified system prompt
- Evaluation results

### 7.7 Report Generation
The evaluation interface must support exporting results as detailed reports:
- Report content must include:
  - Test set identification
  - Model and system prompt configurations
  - Complete evaluation results with:
    - Original prompts
    - Baseline outputs
    - Generated responses
    - Similarity scores
    - LLM evaluation grades
- Reports must be:
  - Easily readable in web browsers
  - Self-contained for sharing
  - Properly formatted for clarity
  - Accessible for future reference

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