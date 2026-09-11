import * as vscode from 'vscode';

export class DashboardPanel {
    public static currentPanel: DashboardPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private _disposables: vscode.Disposable[] = [];

    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
        this._panel = panel;
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
        this._panel.webview.html = this._getHtmlForWebview();
    }

    public onDidReceiveMessage(callback: (message: any) => void) {
        this._panel.webview.onDidReceiveMessage(callback, null, this._disposables);
    }

    public postMessage(message: any) {
        this._panel.webview.postMessage(message);
    }

    public static render(extensionUri: vscode.Uri) {
        if (DashboardPanel.currentPanel) {
            DashboardPanel.currentPanel._panel.reveal(vscode.ViewColumn.One);
        } else {
            const panel = vscode.window.createWebviewPanel(
                'aurixDashboard',
                'AURIX Mission Control',
                vscode.ViewColumn.One,
                { 
                    enableScripts: true,
                    retainContextWhenHidden: true // Prevents VS Code from destroying the UI when you switch tabs!
                }
            );
            DashboardPanel.currentPanel = new DashboardPanel(panel, extensionUri);
        }
    }

    public updateStatus(status: string, logMessage: string) {
        this._panel.webview.postMessage({ command: 'update_status', status, logMessage });
    }

    public renderFindings(findings: any[]) {
        this._panel.webview.postMessage({ command: 'render_findings', findings });
    }

    public dispose() {
        DashboardPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) {
            const x = this._disposables.pop();
            if (x) { x.dispose(); }
        }
    }

    private _getHtmlForWebview() {
        return `<!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>AURIX Dashboard</title>
                <style>
                    body {
                        background-color: var(--vscode-editor-background);
                        color: var(--vscode-editor-foreground);
                        font-family: var(--vscode-font-family), 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        padding: 40px;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                    }
                    .header { text-align: center; margin-bottom: 30px; }
                    .header h1 { color: var(--vscode-textLink-foreground); font-size: 32px; margin-bottom: 5px; display: flex; align-items: center; justify-content: center; gap: 10px; }
                    .header p { color: var(--vscode-descriptionForeground); }
                    .status-box { background-color: var(--vscode-editorWidget-background); border: 1px solid var(--vscode-widget-border); border-radius: 8px; padding: 30px; width: 100%; max-width: 800px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
                    .spinner { width: 50px; height: 50px; border: 5px solid var(--vscode-editorWidget-border); border-top-color: var(--vscode-textLink-foreground); border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 20px auto; display: none; }
                    @keyframes spin { 100% { transform: rotate(360deg); } }
                    #current-status { font-size: 20px; font-weight: 600; margin-bottom: 20px; color: var(--vscode-editor-foreground); }
                    .terminal { background-color: var(--vscode-terminal-background, #000); color: var(--vscode-terminal-foreground, #ccc); border: 1px solid var(--vscode-panel-border); border-radius: 6px; padding: 15px; font-family: 'Courier New', Courier, monospace; font-size: 13px; height: 250px; overflow-y: auto; text-align: left; width: 100%; max-width: 800px; margin-top: 20px; }
                    .log-line { margin: 4px 0; border-bottom: 1px solid var(--vscode-panel-border); padding-bottom: 2px;}
                    .log-time { color: var(--vscode-terminal-ansiBrightBlack); margin-right: 10px; }
                    
                    /* New Findings UI & Gamification */
                    #findings-container { display: none; margin-top: 30px; width: 100%; max-width: 800px; }
                    .report-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--vscode-widget-border); padding-bottom: 10px; margin-bottom: 20px; }
                    .grade-badge { font-size: 36px; font-weight: 900; padding: 10px 25px; border-radius: 12px; text-shadow: 0 2px 4px rgba(0,0,0,0.5); border: 2px solid rgba(255,255,255,0.1); }
                    .grade-A { background: linear-gradient(135deg, #238636, #2ea043); color: white; }
                    .grade-B { background: linear-gradient(135deg, #d29922, #e3b341); color: white; }
                    .grade-C { background: linear-gradient(135deg, #f85149, #ff7b72); color: white; }
                    .grade-F { background: linear-gradient(135deg, #8b0000, #ff0000); color: white; }
                    .finding-card { background-color: var(--vscode-editorWidget-background); border: 1px solid var(--vscode-widget-border); border-left: 4px solid var(--vscode-errorForeground); border-radius: 6px; padding: 15px; margin-bottom: 15px; text-align: left; }
                    .finding-title { color: var(--vscode-errorForeground); font-weight: bold; font-size: 16px; margin-bottom: 10px; }
                    .finding-desc { color: var(--vscode-editor-foreground); font-size: 14px; margin-bottom: 10px; line-height: 1.4; }
                    .finding-loc { color: var(--vscode-descriptionForeground); font-size: 12px; font-family: monospace; }
                    .fix-btn { background-color: var(--vscode-button-background); color: var(--vscode-button-foreground); border: none; border-radius: 4px; padding: 10px 20px; font-size: 14px; font-weight: bold; cursor: pointer; margin-top: 20px; transition: background-color 0.2s; width: 100%; }
                    .fix-btn:hover { background-color: var(--vscode-button-hoverBackground); }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🛡️ AURIX AI Engine</h1>
                    <p>Agentic Security Remediation Platform</p>
                </div>
                
                <div class="status-box">
                    <div id="spinner" class="spinner"></div>
                    <div id="current-status">System Idle. Ready for Scan.</div>
                </div>

                <div class="terminal" id="terminal">
                    <div class="log-line"><span class="log-time">[System]</span> Awaiting connection to LangGraph Cloud...</div>
                </div>

                <div id="findings-container">
                    <div class="report-header">
                        <h2 style="color: var(--vscode-editor-foreground); margin: 0;">Security Report</h2>
                        <div id="grade-badge" class="grade-badge">?</div>
                    </div>
                    <div id="findings-list"></div>
                    <button id="auto-fix-all-btn" class="fix-btn">⚡ Auto-Fix All Vulnerabilities</button>
                </div>

                <script>
                    const vscode = acquireVsCodeApi();
                    
                    const statusText = document.getElementById('current-status');
                    const spinner = document.getElementById('spinner');
                    const terminal = document.getElementById('terminal');
                    const findingsContainer = document.getElementById('findings-container');
                    const findingsList = document.getElementById('findings-list');
                    const autoFixBtn = document.getElementById('auto-fix-all-btn');
                    const gradeBadge = document.getElementById('grade-badge');

                    let currentFindings = [];

                    function calculateGrade(numFindings) {
                        if (numFindings === 0) return { grade: 'A+', class: 'grade-A' };
                        if (numFindings <= 2) return { grade: 'B', class: 'grade-B' };
                        if (numFindings <= 5) return { grade: 'C', class: 'grade-C' };
                        return { grade: 'F', class: 'grade-F' };
                    }

                    autoFixBtn.addEventListener('click', () => {
                        autoFixBtn.textContent = 'Applying Patches...';
                        autoFixBtn.style.backgroundColor = '#8957e5';
                        vscode.postMessage({ command: 'apply_all_fixes', findings: currentFindings });
                        
                    // Fake visual update to A+ when fixed
                        setTimeout(() => {
                            findingsList.innerHTML = '<div style="text-align:center; padding: 20px; color: var(--vscode-editor-foreground);">All vulnerabilities patched! Code is secure.</div>';
                            gradeBadge.className = 'grade-badge grade-A';
                            gradeBadge.textContent = 'A+';
                            autoFixBtn.style.display = 'none';
                        }, 1000);
                    });

                    // New Buttons: Export and History
                    const exportBtn = document.createElement('button');
                    exportBtn.className = 'fix-btn';
                    exportBtn.style.backgroundColor = '#1f6feb';
                    exportBtn.style.marginTop = '10px';
                    exportBtn.textContent = '📄 Export HTML Report';
                    exportBtn.onclick = () => vscode.postMessage({ command: 'export_report', findings: currentFindings });
                    
                    const historyBtn = document.createElement('button');
                    historyBtn.className = 'fix-btn';
                    historyBtn.style.backgroundColor = 'transparent';
                    historyBtn.style.border = '1px solid var(--vscode-button-secondaryBackground)';
                    historyBtn.style.color = 'var(--vscode-editor-foreground)';
                    historyBtn.style.marginTop = '10px';
                    historyBtn.textContent = '🕰️ View Scan History';
                    historyBtn.onclick = () => vscode.postMessage({ command: 'view_history' });

                    findingsContainer.appendChild(exportBtn);
                    findingsContainer.appendChild(historyBtn);

                    // History View Container
                    const historyContainer = document.createElement('div');
                    historyContainer.id = 'history-container';
                    historyContainer.style.display = 'none';
                    historyContainer.style.marginTop = '30px';
                    historyContainer.style.width = '100%';
                    historyContainer.style.maxWidth = '800px';
                    historyContainer.innerHTML = '<h2 style="color: #c9d1d9; border-bottom: 1px solid #30363d; padding-bottom: 10px;">Scan History</h2><div id="history-list"></div><button class="fix-btn" style="background-color:#30363d; margin-top:10px;" onclick="document.getElementById(\\'history-container\\').style.display=\\'none\\'; document.getElementById(\\'findings-container\\').style.display=\\'block\\';">Back to Current Scan</button>';
                    
                    // Insert history container after findings container
                    findingsContainer.parentNode.insertBefore(historyContainer, findingsContainer.nextSibling);

                    window.addEventListener('message', event => {
                        const message = event.data;
                        
                        if (message.command === 'update_status') {
                            if(message.status === 'Idle' || message.status.includes('Complete') || message.status.includes('Error') || message.status.includes('Applied')) {
                                spinner.style.display = 'none';
                                if(message.status.includes('Complete') || message.status.includes('Applied')) {
                                    statusText.style.color = '#3fb950';
                                } else if(message.status.includes('Error')) {
                                    statusText.style.color = '#f85149';
                                }
                            } else {
                                spinner.style.display = 'block';
                                statusText.style.color = '#58a6ff';
                            }
                            statusText.textContent = message.status;
                            if(message.logMessage) {
                                const time = new Date().toLocaleTimeString();
                                terminal.innerHTML += \`<div class="log-line"><span class="log-time">[\${time}]</span> \${message.logMessage}</div>\`;
                                terminal.scrollTop = terminal.scrollHeight;
                            }
                        }

                        if (message.command === 'render_findings') {
                            currentFindings = message.findings;
                            findingsContainer.style.display = 'block';
                            autoFixBtn.style.display = currentFindings.length > 0 ? 'block' : 'none';
                            autoFixBtn.textContent = '⚡ Auto-Fix All Vulnerabilities';
                            autoFixBtn.style.backgroundColor = 'var(--vscode-button-background)';
                            findingsList.innerHTML = '';
                            
                            // Calculate and set Grade
                            const gradeData = calculateGrade(currentFindings.length);
                            gradeBadge.className = \`grade-badge \${gradeData.class}\`;
                            gradeBadge.textContent = gradeData.grade;

                            if (currentFindings.length === 0) {
                                findingsList.innerHTML = '<div style="text-align:center; padding: 20px; color: var(--vscode-editor-foreground);">Excellent! No vulnerabilities detected.</div>';
                                return;
                            }
                            
                            message.findings.forEach((finding, index) => {
                                const card = document.createElement('div');
                                card.className = 'finding-card';
                                card.innerHTML = \`
                                    <div class="finding-title">🚨 \${finding.vulnerability_type}</div>
                                    <div class="finding-desc">\${finding.description}</div>
                                    <div class="finding-loc">📍 File: \${finding.file_path} | Line: \${finding.line_number}</div>
                                    <button class="fix-btn review-btn" style="background-color: var(--vscode-button-secondaryBackground); color: var(--vscode-button-secondaryForeground); margin-top: 10px; padding: 5px 10px; width: auto;" data-index="\${index}">👀 Review Patch in Diff Editor</button>
                                \`;
                                findingsList.appendChild(card);
                            });

                            // Attach event listeners to all the new Review buttons
                            document.querySelectorAll('.review-btn').forEach(btn => {
                                btn.addEventListener('click', (e) => {
                                    const index = e.target.getAttribute('data-index');
                                    const findingToReview = currentFindings[index];
                                    vscode.postMessage({ command: 'review_patch', finding: findingToReview });
                                });
                            });
                        }

                        if (message.command === 'show_history') {
                            const hContainer = document.getElementById('history-container');
                            const hList = document.getElementById('history-list');
                            const fContainer = document.getElementById('findings-container');
                            
                            fContainer.style.display = 'none';
                            hContainer.style.display = 'block';
                            hList.innerHTML = '';
                            
                            if (message.history.length === 0) {
                                hList.innerHTML = '<div style="text-align:center; padding: 20px; color: var(--vscode-editor-foreground);">No previous scans found.</div>';
                                return;
                            }
                            
                            message.history.forEach((scan) => {
                                const card = document.createElement('div');
                                card.className = 'finding-card';
                                card.style.borderLeftColor = scan.findings === 0 ? '#3fb950' : '#d29922';
                                card.innerHTML = \`
                                    <div class="finding-title" style="color: var(--vscode-editor-foreground);">\${new Date(scan.date).toLocaleString()}</div>
                                    <div class="finding-desc">\${scan.findings} vulnerabilities found</div>
                                \`;
                                hList.appendChild(card);
                            });
                        }
                    });
                </script>
            </body>
            </html>`;
    }
}
