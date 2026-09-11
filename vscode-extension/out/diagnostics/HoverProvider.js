"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.AurixHoverProvider = void 0;
const vscode = __importStar(require("vscode"));
class AurixHoverProvider {
    // We store the findings so the hover provider knows what to display
    currentFindings = [];
    updateFindings(findings) {
        this.currentFindings = findings;
    }
    provideHover(document, position, token) {
        // Check if the user is hovering over any line that has a vulnerability
        const finding = this.currentFindings.find(f => f.file_path === document.uri.fsPath &&
            Math.max(0, f.line_number - 1) === position.line);
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
exports.AurixHoverProvider = AurixHoverProvider;
//# sourceMappingURL=HoverProvider.js.map