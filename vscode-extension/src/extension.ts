import * as vscode from 'vscode';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { AurixActionProvider } from './SidebarProvider';
import { AuthManager } from './auth/AuthManager';
import { WorkspaceZipper } from './packager/WorkspaceZipper';
import { ApiConnector } from './api/ApiConnector';
import { DashboardPanel } from './ui/DashboardPanel';
import { DiagnosticsManager, ScanFinding } from './diagnostics/DiagnosticsManager';
import { AurixHoverProvider } from './diagnostics/HoverProvider';

// The Output Logger for debugging natively in the IDE
const outputChannel = vscode.window.createOutputChannel('AURIX Security');

export function activate(context: vscode.ExtensionContext) {
    outputChannel.appendLine('[SYSTEM] AURIX Extension is now active.');

    // Initialize Managers
    const authManager = new AuthManager(context);
    const workspaceZipper = new WorkspaceZipper();
    const apiConnector = new ApiConnector();
    const diagnosticsManager = new DiagnosticsManager(context);
    const hoverProvider = new AurixHoverProvider();

    // Register Hover Provider
    context.subscriptions.push(
        vscode.languages.registerHoverProvider({ scheme: 'file' }, hoverProvider)
    );

    // Register the UI Sidebar
    const aurixActionProvider = new AurixActionProvider();
    vscode.window.registerTreeDataProvider('aurix-actions', aurixActionProvider);

    // ---------------------------------------------------------
    // STATUS BAR ITEM 🛡️
    // ---------------------------------------------------------
    const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.command = 'aurix.scanWorkspace';
    statusBarItem.text = '$(shield) AURIX: Ready';
    statusBarItem.tooltip = 'Click to run an AURIX Security Scan';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);

    // Restore session silently on startup
    authManager.restoreSession().then(async (restored) => {
        if (restored) {
            const user = await authManager.getCurrentUser();
            if (user) {
                statusBarItem.text = `$(shield) AURIX: ${user.email}`;
                outputChannel.appendLine(`[AUTH] Session restored for ${user.email}`);
            }
        }
    });

    // ---------------------------------------------------------
    // COMMAND 1: AURIX Login
    // ---------------------------------------------------------
    let loginDisposable = vscode.commands.registerCommand('aurix.login', async () => {
        outputChannel.appendLine('[INFO] User triggered aurix.login');
        const success = await authManager.login();
        if (success) {
            const user = await authManager.getCurrentUser();
            if (user) {
                statusBarItem.text = `$(shield) AURIX: ${user.email}`;
            }
        }
    });

    // ---------------------------------------------------------
    // COMMAND 1b: AURIX Logout
    // ---------------------------------------------------------
    let logoutDisposable = vscode.commands.registerCommand('aurix.logout', async () => {
        await authManager.logout();
        statusBarItem.text = '$(shield) AURIX: Ready';
    });

    // ---------------------------------------------------------
    // COMMAND 2: AURIX Scan Workspace
    // ---------------------------------------------------------
    let scanDisposable = vscode.commands.registerCommand('aurix.scanWorkspace', async () => {

        // 1. Verify User is Logged In — auto-prompt if not
        let token = await authManager.getToken();
        if (!token) {
            const action = await vscode.window.showWarningMessage(
                'AURIX: You must be logged in to scan.',
                'Login / Sign Up'
            );
            if (action === 'Login / Sign Up') {
                const success = await authManager.login();
                if (!success) { return; }
                const user = await authManager.getCurrentUser();
                if (user) { statusBarItem.text = `$(shield) AURIX: ${user.email}`; }
                token = await authManager.getToken();
            }
            if (!token) { return; }
        }

        // Pop open the glorious new Dashboard UI!
        DashboardPanel.render(context.extensionUri);
        DashboardPanel.currentPanel?.updateStatus('Packaging Workspace...', 'Initializing local File System crawler.');

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

            DashboardPanel.currentPanel?.updateStatus('Uploading to Cloud...', `Workspace safely zipped (${stats.size} bytes). Starting secure transfer.`);
            
            // 3. Upload to Cloud
            try {
                const response = await apiConnector.uploadWorkspace(zipPath, token);
                const scanId = response.scan_id || 'test-scan-id-123'; // fallback for testing
                
                DashboardPanel.currentPanel?.updateStatus('Scan Initialized!', `Cloud payload accepted. Scan ID: ${scanId}`);
                outputChannel.appendLine(`[SUCCESS] Upload successful. Commencing Polling...`);
                
                // 4. Polling Mechanism
                DashboardPanel.currentPanel?.updateStatus('Scanning...', `Waking up AWS LangGraph AI Worker for ${scanId}...`);
                
                const findings = await apiConnector.pollScanStatus(scanId, token, (statusMsg) => {
                    DashboardPanel.currentPanel?.updateStatus('Scanning...', statusMsg);
                    outputChannel.appendLine(`[POLL] ${statusMsg}`);
                });

                // 5. Complete!
                DashboardPanel.currentPanel?.updateStatus('Scan Complete!', `AI Engine found ${findings?.length || 0} vulnerabilities. See Diagnostics.`);
                outputChannel.appendLine(`[DONE] Findings received: ${JSON.stringify(findings)}`);
                
                // 6. Paint the squiggly lines & Update UI!
                if (findings && Array.isArray(findings) && findings.length > 0) {
                    diagnosticsManager.applyFindings(findings as ScanFinding[]);
                    hoverProvider.updateFindings(findings as ScanFinding[]);
                    DashboardPanel.currentPanel?.renderFindings(findings);
                    
                    saveScanToHistory(context, findings.length);

                    DashboardPanel.currentPanel?.onDidReceiveMessage(async (message) => {
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
                            DashboardPanel.currentPanel?.updateStatus('Patches Applied!', 'All vulnerabilities have been neutralized.');
                        } else if (message.command === 'review_patch') {
                            await openDiffPreview(message.finding as ScanFinding);
                        } else if (message.command === 'export_report') {
                            await exportReport(message.findings);
                        } else if (message.command === 'view_history') {
                            const history = context.globalState.get('aurix_scan_history') || [];
                            DashboardPanel.currentPanel?.postMessage({ command: 'show_history', history });
                        }
                    });

                    vscode.window.showWarningMessage(`AURIX: Found ${findings.length} vulnerabilities! Check the Mission Control UI.`);
                } else {
                    vscode.window.showInformationMessage('AURIX: Your code is 100% secure! No vulnerabilities found.');
                }
                
            } catch (error) {
                DashboardPanel.currentPanel?.updateStatus('Upload Error', 'Failed to reach the backend server.');
            } finally {
                // 4. Cleanup the Temp File to save user disk space!
                try {
                    require('fs').unlinkSync(zipPath);
                    outputChannel.appendLine(`[CLEANUP] Deleted temporary zip file at ${zipPath}`);
                } catch (cleanupError) {
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
    
            DashboardPanel.render(context.extensionUri);
            DashboardPanel.currentPanel?.updateStatus('Scanning...', 'Running Offline Mock AI Scan...');
            
            // Wait 2 seconds to simulate work
            await new Promise(resolve => setTimeout(resolve, 2000));
    
            const fakeFindings: ScanFinding[] = [
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
            DashboardPanel.currentPanel?.updateStatus('Scan Complete!', 'Mock Engine found 1 vulnerability. See the Security Report below!');
            DashboardPanel.currentPanel?.renderFindings(fakeFindings);
            
            // Save to history!
            saveScanToHistory(context, fakeFindings.length);

            // Update Status Bar!
            statusBarItem.text = '$(error) AURIX: 1 Vulnerability';
            statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
            
            // Listen for the Auto-Fix button click from the Webview!
            DashboardPanel.currentPanel?.onDidReceiveMessage(async (message) => {
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
                    DashboardPanel.currentPanel?.updateStatus('Patches Applied!', 'All vulnerabilities have been neutralized.');
                    
                    // Reset Status Bar
                    statusBarItem.text = '$(check) AURIX: Secure';
                    statusBarItem.backgroundColor = undefined;
                } else if (message.command === 'review_patch') {
                    await openDiffPreview(message.finding as ScanFinding);
                } else if (message.command === 'export_report') {
                    await exportReport(message.findings);
                } else if (message.command === 'view_history') {
                    const history = context.globalState.get('aurix_scan_history') || [];
                    DashboardPanel.currentPanel?.postMessage({ command: 'show_history', history });
                }
            });

        vscode.window.showWarningMessage('AURIX: Mock scan finished! Check the Mission Control UI.');
    });

    context.subscriptions.push(loginDisposable, logoutDisposable, scanDisposable, mockScanDisposable);
}

export function deactivate() {
    outputChannel.appendLine('[SYSTEM] AURIX Extension deactivated.');
}

/**
 * Creates a temporary file with the AI's fix applied, and opens a split-screen diff!
 */
async function openDiffPreview(finding: ScanFinding) {
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
        await vscode.commands.executeCommand(
            'vscode.diff',
            originalUri,
            patchedUri,
            `AURIX Patch Preview: ${path.basename(finding.file_path)}`
        );
    } catch (error) {
        vscode.window.showErrorMessage('AURIX: Failed to generate Diff Preview.');
        console.error(error);
    }
}

/**
 * Saves a beautifully formatted HTML report to the user's disk!
 */
async function exportReport(findings: ScanFinding[]) {
    const uri = await vscode.window.showSaveDialog({
        defaultUri: vscode.Uri.file('AURIX_Security_Report.html'),
        filters: { 'HTML Files': ['html'] }
    });

    if (!uri) return; // User cancelled

    let html = `<html><head><style>body{font-family:sans-serif;padding:40px;background:#f6f8fa;} .card{background:white;padding:20px;margin-bottom:15px;border-left:4px solid #d73a49;border-radius:6px;box-shadow:0 1px 3px rgba(0,0,0,0.1);}</style></head><body>`;
    html += `<h1>🛡️ AURIX Security Report</h1>`;
    html += `<p>Generated on: ${new Date().toLocaleString()}</p><hr/>`;
    
    if (findings.length === 0) {
        html += `<h2>✅ All Clear! No vulnerabilities found.</h2>`;
    } else {
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
function saveScanToHistory(context: vscode.ExtensionContext, numFindings: number) {
    const history: any[] = context.globalState.get('aurix_scan_history') || [];
    history.unshift({ date: new Date().toISOString(), findings: numFindings });
    if (history.length > 50) history.pop(); // keep last 50
    context.globalState.update('aurix_scan_history', history);
}
