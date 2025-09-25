"""Simple template renderer for Mission Center web interface."""

import re
from pathlib import Path
from typing import Dict, Any

class SimpleTemplateRenderer:
    """A basic template renderer that supports includes and extends."""
    
    def __init__(self, templates_dir: Path):
        self.templates_dir = templates_dir
        self.cache = {}
    
    def render(self, template_name: str, context: Dict[str, Any] = None) -> str:
        """Render a template with optional context."""
        if context is None:
            context = {}
        
        template_path = self.templates_dir / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template {template_name} not found")
        
        content = template_path.read_text(encoding="utf-8")
        return self._process_template(content, context)
    
    def _process_template(self, content: str, context: Dict[str, Any]) -> str:
        """Process template directives."""
        # Handle extends
        extends_match = re.search(r"{% extends ['\"](.+?)['\"] %}", content)
        if extends_match:
            base_template = extends_match.group(1)
            base_content = self.render(base_template, context)

            # Extract blocks from current template
            blocks = self._extract_blocks(content)

            # Replace blocks in base template
            for block_name, block_content in blocks.items():
                processed_block = self._process_includes(block_content, context)
                base_content = re.sub(
                    rf"{{% block {block_name} %}}.*?{{% endblock %}}",
                    processed_block,
                    base_content,
                    flags=re.DOTALL
                )

            # Remove any remaining block definitions and process includes
            base_content = re.sub(r"{% block (\w+) %}(.*?){% endblock %}", r"\2", base_content, flags=re.DOTALL)
            return self._process_includes(base_content, context)
        
        # Handle includes
        content = self._process_includes(content, context)
        
        return content
    
    def _extract_blocks(self, content: str) -> Dict[str, str]:
        """Extract blocks from template content."""
        blocks = {}
        block_pattern = r"{% block (\w+) %}(.*?){% endblock %}"
        
        for match in re.finditer(block_pattern, content, re.DOTALL):
            block_name = match.group(1)
            block_content = match.group(2).strip()
            blocks[block_name] = block_content
        
        return blocks
    
    def _process_includes(self, content: str, context: Dict[str, Any]) -> str:
        """Process include directives."""
        include_pattern = r"{% include ['\"](.+?)['\"] %}"
        
        def replace_include(match):
            include_path = match.group(1)
            try:
                included_content = self.render(include_path, context)
                return included_content
            except FileNotFoundError:
                return f"<!-- Template {include_path} not found -->"
        
        return re.sub(include_pattern, replace_include, content)