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
exports.ApiConnector = void 0;
const vscode = __importStar(require("vscode"));
const axios_1 = __importDefault(require("axios"));
const fs = __importStar(require("fs"));
const form_data_1 = __importDefault(require("form-data"));
class ApiConnector {
    /**
     * Uploads the packaged .zip workspace to Bhavya's Backend
     */
    async uploadWorkspace(zipPath, token) {
        // Fetch the backend URL from VS Code Settings (defaults to the Render production URL)
        const config = vscode.workspace.getConfiguration('aurix');
        const apiEndpoint = config.get('apiEndpoint') || 'https://major-project-yo0n.onrender.com';
        const uploadUrl = `${apiEndpoint}/api/scans/upload`;
        const form = new form_data_1.default();
        form.append('source_code', fs.createReadStream(zipPath), {
            filename: 'workspace.zip',
            contentType: 'application/zip'
        });
        form.append('project_id', '123e4567-e89b-12d3-a456-426614174000'); // Mock UUID for testing
        return await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: "AURIX: Uploading to Cloud",
            cancellable: false
        }, async (progress) => {
            progress.report({ increment: 0, message: "Initiating secure transfer..." });
            try {
                const response = await axios_1.default.post(uploadUrl, form, {
                    headers: {
                        ...form.getHeaders(),
                        'Authorization': `Bearer ${token}`
                    },
                    maxBodyLength: Infinity,
                    maxContentLength: Infinity
                });
                progress.report({ increment: 100, message: "Upload Complete!" });
                return response.data;
            }
            catch (error) {
                console.error(error);
                let errorMessage = 'Failed to upload workspace to AURIX Backend.';
                if (error.response) {
                    errorMessage = `Server Error: ${error.response.status} - ${error.response.data?.detail || error.message}`;
                }
                else if (error.request) {
                    errorMessage = 'Network Error: Backend server is unreachable (it might be spinning up from a cold start).';
                }
                vscode.window.showErrorMessage(errorMessage);
                throw error;
            }
        });
    }
    /**
     * Polls the backend every 5 seconds to check if the LangGraph AI has finished scanning.
     */
    async pollScanStatus(scanId, token, onUpdate) {
        const config = vscode.workspace.getConfiguration('aurix');
        const apiEndpoint = config.get('apiEndpoint') || 'https://major-project-yo0n.onrender.com';
        const pollUrl = `${apiEndpoint}/api/scans/${scanId}`;
        return new Promise((resolve, reject) => {
            const interval = setInterval(async () => {
                try {
                    const response = await axios_1.default.get(pollUrl, {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    const status = response.data.status;
                    if (status === 'COMPLETED') {
                        clearInterval(interval);
                        resolve(response.data.findings);
                    }
                    else if (status === 'FAILED') {
                        clearInterval(interval);
                        reject(new Error('AI Engine failed to process the scan.'));
                    }
                    else {
                        // PENDING or SCANNING
                        onUpdate(`AI Engine Status: ${status}...`);
                    }
                }
                catch (error) {
                    console.error('Polling error:', error);
                    // Don't clear interval on network errors, might just be a temporary blip
                }
            }, 5000);
        });
    }
}
exports.ApiConnector = ApiConnector;
//# sourceMappingURL=ApiConnector.js.map