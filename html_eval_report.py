"""Module for generating HTML evaluation reports with markdown support."""

import markdown
from typing import List, Dict

class HtmlEvalReport:
    """Class for generating HTML evaluation reports with markdown support."""
    
    def __init__(self):
        self.md = markdown.Markdown(extensions=['tables', 'fenced_code'])
        
    def generate_report(self, evaluation_results: List[Dict], metadata: Dict[str, str]) -> str:
        """Generate an HTML report from evaluation results.
        
        Args:
            evaluation_results: List of dictionaries containing evaluation results
                              Each dict should have: input_text, baseline_output,
                              current_output, similarity_score, and llm_grade
            metadata: Dictionary containing evaluation metadata:
                     - test_set_name: Name of the test set used
                     - baseline_system_prompt: System prompt used for baseline results
                     - new_system_prompt: System prompt used for comparison evaluation
                     - model_name: Name of the LLM model used
        
        Returns:
            str: Complete HTML document as a string
        """
        html_content = self._get_html_header()
        html_content += self._generate_metadata_section(metadata)
        html_content += self._generate_table_content(evaluation_results)
        html_content += self._get_html_footer()
        return html_content
    
    def _get_html_header(self) -> str:
        """Get the HTML header with CSS styling."""
        return """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
                th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
                th { background-color: #f5f5f5; }
                tr:nth-child(even) { background-color: #f9f9f9; }
                .score { text-align: center; }
                pre { background-color: #f8f8f8; padding: 10px; border-radius: 4px; }
                code { background-color: #f0f0f0; padding: 2px 4px; border-radius: 2px; }
                .metadata { 
                    background-color: #f5f5f5;
                    padding: 15px;
                    border-radius: 4px;
                    margin: 20px 0;
                }
                .metadata h2 {
                    margin-top: 0;
                    color: #333;
                    margin-bottom: 15px;
                }
                .metadata dl {
                    margin: 0;
                    display: grid;
                    grid-template-columns: 200px 1fr;
                    gap: 8px 15px;
                    align-items: start;
                }
                .metadata dt {
                    font-weight: bold;
                    color: #666;
                    padding: 4px 0;
                }
                .metadata dd {
                    margin: 0;
                    padding: 4px 0;
                }
                .metadata dd p {
                    margin: 0;
                }
            </style>
        </head>
        <body>
            <h1>Evaluation Results</h1>
        """
    
    def _generate_metadata_section(self, metadata: Dict[str, str]) -> str:
        """Generate the HTML for the metadata section."""
        return f"""
            <div class="metadata">
                <h2>Evaluation Details</h2>
                <dl>
                    <dt>Test Set:</dt>
                    <dd>{metadata.get('test_set_name', 'N/A')}</dd>
                    
                    <dt>Model:</dt>
                    <dd>{metadata.get('model_name', 'N/A')}</dd>
                    
                    <dt>Baseline System Prompt:</dt>
                    <dd>{self.md.convert(metadata.get('baseline_system_prompt', 'N/A'))}</dd>

                    <dt>New System Prompt:</dt>
                    <dd>{self.md.convert(metadata.get('new_system_prompt', 'N/A'))}</dd>
                </dl>
            </div>
            <table>
                <tr>
                    <th>Input Text</th>
                    <th>Baseline Output</th>
                    <th>New Output</th>
                    <th>Similarity Score</th>
                    <th>LLM Grade</th>
                </tr>
        """
    
    def _generate_table_content(self, evaluation_results: List[Dict]) -> str:
        """Generate the HTML table content from evaluation results."""
        content = ""
        for result in evaluation_results:
            content += f"""
                <tr>
                    <td>{self.md.convert(result['input_text'])}</td>
                    <td>{self.md.convert(result['baseline_output'])}</td>
                    <td>{self.md.convert(result['current_output'])}</td>
                    <td class="score">{result['similarity_score']:.2f}</td>
                    <td>{result['llm_grade']}</td>
                </tr>
            """
            # Reset the markdown converter for the next iteration
            self.md.reset()
        return content
    
    def _get_html_footer(self) -> str:
        """Get the HTML footer."""
        return """
            </table>
        </body>
        </html>
        """
