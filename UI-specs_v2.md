# Prompt Nanny UI Specification

## 1. Application Structure and Navigation
The PromptNanny UI consists of three main parts, each accessible through a tab control located at the top left of the main window:
- **Prompts Catalog**
- **LLM Playground**
- **Eval Playground**

## 2. Global UI Guidelines and Behaviors

### 2.1 Expandable/Collapsible Groups
When implementing UI element groups that support expand/collapse functionality, the following rules apply:
- In the collapsed state, all contents including headers must be hidden, with only the expand/collapse button remaining visible
- The expand/collapse button must be positioned at the top-right of the group area
- The button must use chevron icons from the Lucide icon set to indicate state:
  - Collapsed: ChevronRight icon (→)
  - Expanded: ChevronLeft icon (←)
- When collapsed, the group width should be exactly 48px to accommodate the chevron button
- The transition between states should be animated with a duration of 200ms

### 2.2 State Persistence
The application must maintain the following states between user sessions:
- Expand/collapse states for all collapsible groups
- The most recently selected prompt in the Prompts Catalog
- All LLM parameter settings (Temperature, Max Tokens, Stream setting)
- The selected LLM model
- System Prompt visibility state and content

### 2.3 Visual Styling Standards
To maintain consistency across the application:
- All text input areas must use 16px padding and a minimum height of 100px for multiline inputs
- Visual borders around main interaction areas must use a light gray color (#E5E7EB) with 1px width
- Spacing between major UI elements must be consistently 16px
- Input fields must have a consistent height of 40px for single-line inputs
- All interactive elements must show hover and focus states with a subtle background color change (#F3F4F6)

## 3. Prompts Catalog Implementation

### 3.1 Left-Side Group
The collapsible group on the left side must:
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

### 4.1 Parameter Controls Group
The left-side parameter group must:
- Default to collapsed state on first application launch
- Implement the Temperature slider with:
  - Range from 0 to 1
  - Step size of 0.1
  - Visual indication of the current value
  - Numerical input option for precise control
- The Max Tokens field must:
  - Accept only positive integers
  - Show an error state for invalid inputs
  - Provide a reasonable maximum limit based on the selected model

### 4.2 Main Interaction Area
The playground workspace must implement:

#### System Prompt Section
- The checkbox controls complete visibility of the System Prompt text area
- The text area must animate smoothly when shown/hidden
- When hidden, the space must collapse to prevent empty gaps in the layout

#### User Prompt Section
- Must reflect the Current Prompt from the Prompts Catalog when specified
- Must maintain a separate history of edits from the original prompt
- Must provide a "Reset to Original" option when modified from a Current Prompt

#### Response Handling
The response area must:
- Render markdown formatting in real-time using a standard markdown parser
- When streaming is enabled:
  - Show a typing indicator during response generation
  - Render markdown elements as they complete (not character by character)
  - Provide a "Stop Generation" button during streaming
- Display character and token counts below the response area
- Include a copy button in the top-right corner
- Support syntax highlighting for code blocks
- Maintain scroll position when content updates

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

## 7. Eval Playground
The specific UI implementation for the Eval Playground remains to be defined, but it must maintain consistency with the established patterns and behaviors defined in this specification.