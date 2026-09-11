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
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.WorkspaceZipper = void 0;
const vscode = __importStar(require("vscode"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const os = __importStar(require("os"));
const archiver = require('archiver');
const ignore_1 = __importDefault(require("ignore"));
class WorkspaceZipper {
    /**
     * Packages the current workspace into a .zip file, strictly adhering to .gitignore.
     */
    async packageWorkspace() {
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
            return new Promise((resolve, reject) => {
                const output = fs.createWriteStream(tempZipPath);
                const archive = archiver('zip', { zlib: { level: 5 } });
                output.on('close', () => {
                    resolve(tempZipPath);
                });
                archive.on('error', (err) => {
                    reject(err);
                });
                archive.pipe(output);
                progress.report({ increment: 30, message: "Compressing files (ignoring node_modules)..." });
                // Setup Git Ignore logic safely
                const ig = (0, ignore_1.default)().add(['.git', 'node_modules', 'venv', 'aurix-vscode']);
                const gitignorePath = path.join(rootPath, '.gitignore');
                if (fs.existsSync(gitignorePath)) {
                    ig.add(fs.readFileSync(gitignorePath, 'utf8'));
                }
                // Bulletproof Recursive Walker
                const walkSync = (dir) => {
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
                        }
                        else {
                            archive.file(fullPath, { name: relativePath });
                        }
                    }
                };
                try {
                    walkSync(rootPath);
                }
                catch (e) {
                    console.error("Walker Error:", e);
                }
                archive.finalize();
            });
        });
    }
}
exports.WorkspaceZipper = WorkspaceZipper;
//# sourceMappingURL=WorkspaceZipper.js.map