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
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const fs = __importStar(require("fs"));
const os = __importStar(require("os"));
const path = __importStar(require("path"));
const SidebarProvider_1 = require("./SidebarProvider");
const AuthManager_1 = require("./auth/AuthManager");
const WorkspaceZipper_1 = require("./packager/WorkspaceZipper");
const ApiConnector_1 = require("./api/ApiConnector");
const DashboardPanel_1 = require("./ui/DashboardPanel");
const DiagnosticsManager_1 = require("./diagnostics/DiagnosticsManager");
const HoverProvider_1 = require("./diagnostics/HoverProvider");
// The Output Logger for debugging natively in the IDE
const outputChannel = vscode.window.createOutputChannel('AURIX Security');
function activate(context) {
    outputChannel.appendLine('[SYSTEM] AURIX Extension is now active.');
    // Initialize Managers
    const authManager = new AuthManager_1.AuthManager(context);
    const workspaceZipper = new WorkspaceZipper_1.WorkspaceZipper();
    const apiConnector = new ApiConnector_1.ApiConnector();
    const diagnosticsManager = new DiagnosticsManager_1.DiagnosticsManager(context);
    const hoverProvider = new HoverProvider_1.AurixHoverProvider();
    // Register Hover Provider
    context.subscriptions.push(vscode.languages.registerHoverProvider({ scheme: 'file' }, hoverProvider));
    // Register the UI Sidebar
    const aurixActionProvider = new SidebarProvider_1.AurixActionProvider();
    vscode.window.registerTreeDataProvider('aurix-actions', aurixActionProvider);
    // ---------------------------------------------------------
    // STATUS BAR ITEM 🛡️
    // ---------------------------------------------------------
    const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.command = 'aurix.scanWorkspace'; // Clicking it triggers a scan!
    statusBarItem.text = '$(shield) AURIX: Ready';
    statusBarItem.tooltip = 'Click to run an AURIX Security Scan';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);
    // ---------------------------------------------------------
    // COMMAND 1: AURIX Login
    // ---------------------------------------------------------
    let loginDisposable = vscode.commands.registerCommand('aurix.login', async () => {
        outputChannel.appendLine('[INFO] User triggered aurix.login');
        await authManager.login();
    });
    // ---------------------------------------------------------
    // COMMAND 2: AURIX Scan Workspace
    // ---------------------------------------------------------
    let scanDisposable = vscode.commands.registerCommand('aurix.scanWorkspace', async () => {
        // 1. Verify User is Logged In
        const token = await authManager.getToken();
        if (!token) {
            vscode.window.showErrorMessage('AURIX: You must login first before scanning!');
            return;
        }
        // Pop open the glorious new Dashboard UI!
        DashboardPanel_1.DashboardPanel.render(context.extensionUri);
        DashboardPanel_1.DashboardPanel.currentPanel?.updateStatus('Packaging Workspace...', 'Initializing local File System crawler.');
        // 2. Zip the Workspace securely
        outputChannel.appendLine('[INFO] Starting Workspace Packager...');
        const zipPath = await workspaceZipper.packageWorkspace();
        if (zipPath) {
            const stats = require('fs').statSync(zipPath);
            outputChannel.appendLine(`[SUCCESS] Zip created at: ${zipPath}. Size: ${stats.size} bytes`);
            if (stats.size < 100) {
                vscode.window.showErrorMessage(`Zip file is empty (${stats.size} bytes). Archiver failed to add files!`);
                return;
            }
            DashboardPanel_1.DashboardPanel.currentPanel?.updateStatus('Uploading to Cloud...', `Workspace safely zipped (${stats.size} bytes). Starting secure transfer.`);
            // 3. Upload to Cloud
            try {
                const response = await apiConnector.uploadWorkspace(zipPath, token);
                const scanId = response.scan_id || 'test-scan-id-123'; // fallback for testing
                DashboardPanel_1.DashboardPanel.currentPanel?.updateStatus('Scan Initialized!', `Cloud payload accepted. Scan ID: ${scanId}`);
                outputChannel.appendLine(`[SUCCESS] Upload successful. Commencing Polling...`);
                // 4. Polling Mechanism
                DashboardPanel_1.DashboardPanel.currentPanel?.updateStatus('Scanning...', `Waking up AWS LangGraph AI Worker for ${scanId}...`);
                const findings = await apiConnector.pollScanStatus(scanId, token, (statusMsg) => {
                    DashboardPanel_1.DashboardPanel.currentPanel?.updateStatus('Scanning...', statusMsg);
                    outputChannel.appendLine(`[POLL] ${statusMsg}`);
                });
                // 5. Complete!
                DashboardPanel_1.DashboardPanel.currentPanel?.updateStatus('Scan Complete!', `AI Engine found ${findings?.length || 0} vulnerabilities. See Diagnostics.`);
                outputChannel.appendLine(`[DONE] Findings received: ${JSON.stringify(findings)}`);
                // 6. Paint the squiggly lines & Update UI!
                if (findings && Array.isArray(findings) && findings.length > 0) {
                    diagnosticsManager.applyFindings(findings);
                    hoverProvider.updateFindings(findings);
                    DashboardPanel_1.DashboardPanel.currentPanel?.renderFindings(findings);
                    saveScanToHistory(context, findings.length);
                    DashboardPanel_1.DashboardPanel.currentPanel?.onDidReceiveMessage(async (message) => {
                        if (message.command === 'apply_all_fixes') {
                            const edit = new vscode.WorkspaceEdit();
                            for (const finding of message.findings) {
                                const uri = vscode.Uri.file(finding.file_path);
                                const line = Math.max(0, finding.line_number - 1);
                                const range = new vscode.Range(line, 0, line, 100);
                                edit.replace(uri, range, finding.suggested_fix);
                            }
                            await vscode.workspace.applyEdit(edit);
                            vscode.window.showInformationMessage('AURIX: All AI Patches Applied Successfully!');
                            DashboardPanel_1.DashboardPanel.currentPanel?.updateStatus('Patches Applied!', 'All vulnerabilities have been neutralized.');
                        }
                        else if (message.command === 'review_patch') {
                            await openDiffPreview(message.finding);
                        }
                        else if (message.command === 'export_report') {
                            await exportReport(message.findings);
                        }
                        else if (message.command === 'view_history') {
                            const history = context.globalState.get('aurix_scan_history') || [];
                            DashboardPanel_1.DashboardPanel.currentPanel?.postMessage({ command: 'show_history', history });
                        }
                    });
                    vscode.window.showWarningMessage(`AURIX: Found ${findings.length} vulnerabilities! Check the Mission Control UI.`);
                }
                else {
                    vscode.window.showInformationMessage('AURIX: Your code is 100% secure! No vulnerabilities found.');
                }
            }
            catch (error) {
                DashboardPanel_1.DashboardPanel.currentPanel?.updateStatus('Upload Error', 'Failed to reach the backend server.');
            }
            finally {
                // 4. Cleanup the Temp File to save user disk space!
                try {
                    require('fs').unlinkSync(zipPath);
                    outputChannel.appendLine(`[CLEANUP] Deleted temporary zip file at ${zipPath}`);
                }
                catch (cleanupError) {
                    outputChannel.appendLine(`[WARNING] Failed to delete temporary zip file: ${cleanupError}`);
                }
            }
        }
    });
    // ---------------------------------------------------------
    // COMMAND 3: AURIX Mock Scan (Offline Testing)
    // ---------------------------------------------------------
    let mockScanDisposable = vscode.commands.registerCommand('aurix.mockScan', async () => {
        statusBarItem.text = '$(sync~spin) AURIX: Scanning...';
        // We MUST grab the editor BEFORE we open the Mission Control webview, 
        // otherwise the webview steals focus and activeTextEditor becomes undefined!
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage("AURIX: Please open a code file first to test the mock scan!");
            statusBarItem.text = '$(shield) AURIX: Ready';
            return;
        }
        DashboardPanel_1.DashboardPanel.render(context.extensionUri);
        DashboardPanel_1.DashboardPanel.currentPanel?.updateStatus('Scanning...', 'Running Offline Mock AI Scan...');
        // Wait 2 seconds to simulate work
        await new Promise(resolve => setTimeout(resolve, 2000));
        const fakeFindings = [
            {
                file_path: editor.document.uri.fsPath,
                line_number: 1, // Put it on line 1
                vulnerability_type: "SQL Injection",
                description: "Mock Vulnerability: This code is susceptible to a mock SQL injection.",
                suggested_fix: "# [AURIX AI PATCH APPLIED]\n# Secure parameterized query implemented.\n"
            }
        ];
        diagnosticsManager.applyFindings(fakeFindings);
        hoverProvider.updateFindings(fakeFindings);
        DashboardPanel_1.DashboardPanel.currentPanel?.updateStatus('Scan Complete!', 'Mock Engine found 1 vulnerability. See the Security Report below!');
        DashboardPanel_1.DashboardPanel.currentPanel?.renderFindings(fakeFindings);
        // Save to history!
        saveScanToHistory(context, fakeFindings.length);
        // Update Status Bar!
        statusBarItem.text = '$(error) AURIX: 1 Vulnerability';
        statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
        // Listen for the Auto-Fix button click from the Webview!
        DashboardPanel_1.DashboardPanel.currentPanel?.onDidReceiveMessage(async (message) => {
            if (message.command === 'apply_all_fixes') {
                const edit = new vscode.WorkspaceEdit();
                for (const finding of message.findings) {
                    const uri = vscode.Uri.file(finding.file_path);
                    const line = Math.max(0, finding.line_number - 1);
                    const range = new vscode.Range(line, 0, line, 100);
                    edit.replace(uri, range, finding.suggested_fix);
                }
                await vscode.workspace.applyEdit(edit);
                vscode.window.showInformationMessage('AURIX: All AI Patches Applied Successfully!');
                DashboardPanel_1.DashboardPanel.currentPanel?.updateStatus('Patches Applied!', 'All vulnerabilities have been neutralized.');
                // Reset Status Bar
                statusBarItem.text = '$(check) AURIX: Secure';
                statusBarItem.backgroundColor = undefined;
            }
            else if (message.command === 'review_patch') {
                await openDiffPreview(message.finding);
            }
            else if (message.command === 'export_report') {
                await exportReport(message.findings);
            }
            else if (message.command === 'view_history') {
                const history = context.globalState.get('aurix_scan_history') || [];
                DashboardPanel_1.DashboardPanel.currentPanel?.postMessage({ command: 'show_history', history });
            }
        });
        vscode.window.showWarningMessage('AURIX: Mock scan finished! Check the Mission Control UI.');
    });
    context.subscriptions.push(loginDisposable, scanDisposable, mockScanDisposable);
}
function deactivate() {
    outputChannel.appendLine('[SYSTEM] AURIX Extension deactivated.');
}
/**
 * Creates a temporary file with the AI's fix applied, and opens a split-screen diff!
 */
async function openDiffPreview(finding) {
    try {
        const originalUri = vscode.Uri.file(finding.file_path);
        // 1. Read the original file
        const document = await vscode.workspace.openTextDocument(originalUri);
        const originalText = document.getText();
        const lines = originalText.split(/\r?\n/);
        // 2. Apply the AI's fix in memory
        const lineIndex = Math.max(0, finding.line_number - 1);
        if (lineIndex < lines.length) {
            lines[lineIndex] = finding.suggested_fix;
        }
        const patchedText = lines.join('\n');
        // 3. Save the patched code to a temporary file
        const tempFilename = `aurix_preview_${path.basename(finding.file_path)}`;
        const tempPath = path.join(os.tmpdir(), tempFilename);
        fs.writeFileSync(tempPath, patchedText);
        const patchedUri = vscode.Uri.file(tempPath);
        // 4. Trigger VS Code Native Diff Editor
        await vscode.commands.executeCommand('vscode.diff', originalUri, patchedUri, `AURIX Patch Preview: ${path.basename(finding.file_path)}`);
    }
    catch (error) {
        vscode.window.showErrorMessage('AURIX: Failed to generate Diff Preview.');
        console.error(error);
    }
}
/**
 * Saves a beautifully formatted HTML report to the user's disk!
 */
async function exportReport(findings) {
    const uri = await vscode.window.showSaveDialog({
        defaultUri: vscode.Uri.file('AURIX_Security_Report.html'),
        filters: { 'HTML Files': ['html'] }
    });
    if (!uri)
        return; // User cancelled
    let html = `<html><head><style>body{font-family:sans-serif;padding:40px;background:#f6f8fa;} .card{background:white;padding:20px;margin-bottom:15px;border-left:4px solid #d73a49;border-radius:6px;box-shadow:0 1px 3px rgba(0,0,0,0.1);}</style></head><body>`;
    html += `<h1>🛡️ AURIX Security Report</h1>`;
    html += `<p>Generated on: ${new Date().toLocaleString()}</p><hr/>`;
    if (findings.length === 0) {
        html += `<h2>✅ All Clear! No vulnerabilities found.</h2>`;
    }
    else {
        findings.forEach(f => {
            html += `<div class="card">
                <h3 style="color:#d73a49;margin-top:0;">🚨 ${f.vulnerability_type}</h3>
                <p><b>Description:</b> ${f.description}</p>
                <p><code>File: ${f.file_path} | Line: ${f.line_number}</code></p>
            </div>`;
        });
    }
    html += `</body></html>`;
    fs.writeFileSync(uri.fsPath, html);
    vscode.window.showInformationMessage(`AURIX: Report exported successfully to ${uri.fsPath}!`);
}
/**
 * Saves the scan to global state history.
 */
function saveScanToHistory(context, numFindings) {
    const history = context.globalState.get('aurix_scan_history') || [];
    history.unshift({ date: new Date().toISOString(), findings: numFindings });
    if (history.length > 50)
        history.pop(); // keep last 50
    context.globalState.update('aurix_scan_history', history);
}
//# sourceMappingURL=extension.js.map