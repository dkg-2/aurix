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
exports.DiagnosticsManager = void 0;
const vscode = __importStar(require("vscode"));
class DiagnosticsManager {
    diagnosticCollection;
    constructor(context) {
        // 1. Create a collection to hold our red squiggly lines
        this.diagnosticCollection = vscode.languages.createDiagnosticCollection('aurix');
        context.subscriptions.push(this.diagnosticCollection);
        // 2. Register this class as the provider for the "Lightbulb" quick-fixes!
        context.subscriptions.push(vscode.languages.registerCodeActionsProvider({ scheme: 'file' }, // Works on all local files
        this, { providedCodeActionKinds: [vscode.CodeActionKind.QuickFix] }));
    }
    /**
     * Called by the extension when the AI finishes a scan.
     * Takes the JSON array of findings and paints red squiggles on the exact lines!
     */
    applyFindings(findings) {
        this.diagnosticCollection.clear();
        // Group findings by file
        const diagnosticsByFile = new Map();
        for (const finding of findings) {
            // VS Code line numbers are 0-indexed, so we subtract 1
            const line = Math.max(0, finding.line_number - 1);
            // We highlight the entire line from column 0 to 100
            const range = new vscode.Range(line, 0, line, 100);
            // Create the red squiggly error
            const diagnostic = new vscode.Diagnostic(range, `[AURIX AI] ${finding.vulnerability_type}: ${finding.description}`, vscode.DiagnosticSeverity.Error);
            diagnostic.source = 'AURIX';
            diagnostic.code = finding.suggested_fix; // We temporarily hide the AI's patch inside the diagnostic's 'code' property!
            // Add to the map
            const uri = vscode.Uri.file(finding.file_path);
            const uriString = uri.toString();
            if (!diagnosticsByFile.has(uriString)) {
                diagnosticsByFile.set(uriString, []);
            }
            diagnosticsByFile.get(uriString)?.push(diagnostic);
        }
        // Apply all squiggly lines to the editor
        for (const [uriString, diagnostics] of diagnosticsByFile.entries()) {
            this.diagnosticCollection.set(vscode.Uri.parse(uriString), diagnostics);
        }
    }
    /**
     * VS Code automatically calls this when the user clicks the Lightbulb 💡
     * We return a "Quick Fix" action that replaces the bad code with the AI's patch!
     */
    provideCodeActions(document, range, context, token) {
        const actions = [];
        // Look at all the red squiggles the user is currently hovering over
        for (const diagnostic of context.diagnostics) {
            if (diagnostic.source === 'AURIX' && diagnostic.code) {
                // Extract the AI's suggested patch we hid earlier
                const suggestedPatch = diagnostic.code;
                // Create the glowing Quick Fix button
                const action = new vscode.CodeAction('⚡ AURIX: Apply AI Security Patch', vscode.CodeActionKind.QuickFix);
                action.edit = new vscode.WorkspaceEdit();
                action.diagnostics = [diagnostic];
                action.isPreferred = true; // Makes it pop up first!
                // Tell VS Code to replace the entire line with the new AI code
                action.edit.replace(document.uri, diagnostic.range, suggestedPatch);
                actions.push(action);
            }
        }
        return actions;
    }
}
exports.DiagnosticsManager = DiagnosticsManager;
//# sourceMappingURL=DiagnosticsManager.js.map