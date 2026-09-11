import * as vscode from 'vscode';
import { ScanFinding } from './DiagnosticsManager';

export class AurixHoverProvider implements vscode.HoverProvider {
    
    // We store the findings so the hover provider knows what to display
    private currentFindings: ScanFinding[] = [];

    public updateFindings(findings: ScanFinding[]) {
        this.currentFindings = findings;
    }

    public provideHover(
        document: vscode.TextDocument,
        position: vscode.Position,
        token: vscode.CancellationToken
    ): vscode.ProviderResult<vscode.Hover> {
        
        // Check if the user is hovering over any line that has a vulnerability
        const finding = this.currentFindings.find(f => 
            f.file_path === document.uri.fsPath && 
            Math.max(0, f.line_number - 1) === position.line
        );

        if (!finding) {
            return null; // No vulnerability on this line
        }

        // Build a beautiful rich Markdown tooltip
        const markdown = new vscode.MarkdownString();
        markdown.isTrusted = true;
        markdown.supportHtml = true;

        markdown.appendMarkdown(`## 🛡️ AURIX Security Alert\n\n`);
        markdown.appendMarkdown(`**🚨 Vulnerability:** \`<span style="color:#f85149;">${finding.vulnerability_type}</span>\`\n\n`);
        markdown.appendMarkdown(`**Description:** ${finding.description}\n\n`);
        markdown.appendMarkdown(`---\n\n`);
        
        // Add a link to OWASP based on common vulnerabilities
        const searchUrl = `https://owasp.org/search/?searchString=${encodeURIComponent(finding.vulnerability_type)}`;
        markdown.appendMarkdown(`[📚 Read the official OWASP Documentation for this vulnerability](${searchUrl})\n\n`);
        
        // Add a hint about the Quick Fix
        markdown.appendMarkdown(`*💡 Hint: Click the yellow lightbulb to Auto-Fix this code, or use the Mission Control dashboard.*`);

        return new vscode.Hover(markdown);
    }
}
