import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
const archiver = require('archiver');
import ignore from 'ignore';

export class WorkspaceZipper {
    
    /**
     * Packages the current workspace into a .zip file, strictly adhering to .gitignore.
     */
    public async packageWorkspace(): Promise<string | undefined> {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders || workspaceFolders.length === 0) {
            vscode.window.showErrorMessage('AURIX: No workspace folder open.');
            return undefined;
        }

        const rootPath = workspaceFolders[0].uri.fsPath;
        const tempZipPath = path.join(os.tmpdir(), `aurix_workspace_${Date.now()}.zip`);

        return await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: "AURIX: Packaging Workspace",
            cancellable: false
        }, async (progress) => {
            progress.report({ increment: 0, message: "Parsing .gitignore..." });

            return new Promise<string>((resolve, reject) => {
                const output = fs.createWriteStream(tempZipPath);
                const archive = archiver('zip', { zlib: { level: 5 } }); 

                output.on('close', () => {
                    resolve(tempZipPath);
                });

                archive.on('error', (err: any) => {
                    reject(err);
                });

                archive.pipe(output);


                progress.report({ increment: 30, message: "Compressing files (ignoring node_modules)..." });

                // Setup Git Ignore logic safely
                const ig = ignore().add(['.git', 'node_modules', 'venv', 'aurix-vscode']);
                const gitignorePath = path.join(rootPath, '.gitignore');
                if (fs.existsSync(gitignorePath)) {
                    ig.add(fs.readFileSync(gitignorePath, 'utf8'));
                }

                // Bulletproof Recursive Walker
                const walkSync = (dir: string) => {
                    const files = fs.readdirSync(dir);
                    for (const file of files) {
                        const fullPath = path.join(dir, file);
                        const relativePath = path.relative(rootPath, fullPath).replace(/\\/g, '/');

                        if (ig.ignores(relativePath)) {
                            continue;
                        }

                        const stat = fs.statSync(fullPath);
                        if (stat.isDirectory()) {
                            walkSync(fullPath);
                        } else {
                            archive.file(fullPath, { name: relativePath });
                        }
                    }
                };

                try {
                    walkSync(rootPath);
                } catch (e) {
                    console.error("Walker Error:", e);
                }

                archive.finalize();
            });
        });
    }
}
