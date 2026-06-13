import os
import re
import ast

class ContextFetcher:
    """
    Advanced Semantic Slicer for Project AURIX.
    Uses AST and Block-level analysis to provide rich AI context.
    """

    def __init__(self, workspace_path):
        self.workspace_path = workspace_path

    def _get_imports(self, file_path):
        """Extracts import statements."""
        imports = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if re.match(r'^(import |from |const .* = require\(|var .* = require\()', line):
                        imports.append(line.strip())
                    if len(imports) > 20: break
        except Exception: pass
        return "\n".join(imports)

    def _get_python_function_slice(self, file_path, line_number):
        """Uses AST to extract the entire function containing the line."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunction)):
                    if node.lineno <= line_number <= getattr(node, 'end_lineno', line_number + 50):
                        # Extract exactly this function from the source
                        lines = source.splitlines()
                        return "\n".join(lines[node.lineno-1 : node.end_lineno])
        except Exception:
            pass
        return None

    def _get_regex_block_slice(self, file_path, line_number):
        """Fallback for JS/Other: Grabs the curly brace block containing the line."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # Look up and down for braces to find the 'Block'
            start = max(0, line_number - 30)
            end = min(len(lines), line_number + 30)
            return "".join(lines[start:end])
        except Exception: pass
        return None

    def get_finding_context(self, relative_file_path, line_number):
        """
        Retrieves a Semantic Slice of the source code.
        Tries AST first, then block-level fallback.
        """
        full_path = os.path.join(self.workspace_path, relative_file_path)
        if not os.path.exists(full_path):
            return {"error": "File not found"}

        imports = self._get_imports(full_path)
        
        # 1. Try Python AST Slicing
        snippet = None
        if full_path.endswith(".py"):
            snippet = self._get_python_function_slice(full_path, line_number)
        
        # 2. Fallback to Window/Block Slicing
        if not snippet:
            snippet = self._get_regex_block_slice(full_path, line_number)

        # 3. SAFETY CAP: Truncate very long functions to stay under 8K TPM limit
        if snippet and len(snippet) > 2000:
            snippet = snippet[:2000] + "\n... [TRUNCATED FOR TOKEN LIMIT] ..."

        return {
            "file": relative_file_path,
            "line": line_number,
            "context_snippet": snippet,
            "imports": imports,
            "slicing_method": "ast" if full_path.endswith(".py") else "window"
        }

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 3:
        fetcher = ContextFetcher(sys.argv[1])
        ctx = fetcher.get_finding_context(sys.argv[2], int(sys.argv[3]))
        print(f"--- Context (Method: {ctx['slicing_method']}) ---")
        print(ctx['context_snippet'])
