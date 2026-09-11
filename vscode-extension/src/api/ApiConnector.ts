import * as vscode from 'vscode';
import axios from 'axios';
import * as fs from 'fs';
import FormData from 'form-data';

export class ApiConnector {
    
    /**
     * Uploads the packaged .zip workspace to Bhavya's Backend
     */
    public async uploadWorkspace(zipPath: string, token: string): Promise<any> {
        // Fetch the backend URL from VS Code Settings (defaults to the Render production URL)
        const config = vscode.workspace.getConfiguration('aurix');
        const apiEndpoint = config.get<string>('apiEndpoint') || 'https://major-project-yo0n.onrender.com';
        const uploadUrl = `${apiEndpoint}/api/scans/upload`;

        const form = new FormData();
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
                const response = await axios.post(uploadUrl, form, {
                    headers: {
                        ...form.getHeaders(),
                        'Authorization': `Bearer ${token}`
                    },
                    maxBodyLength: Infinity,
                    maxContentLength: Infinity
                });

                progress.report({ increment: 100, message: "Upload Complete!" });
                return response.data;
                
            } catch (error: any) {
                console.error(error);
                let errorMessage = 'Failed to upload workspace to AURIX Backend.';
                if (error.response) {
                    errorMessage = `Server Error: ${error.response.status} - ${error.response.data?.detail || error.message}`;
                } else if (error.request) {
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
    public async pollScanStatus(scanId: string, token: string, onUpdate: (status: string) => void): Promise<any> {
        const config = vscode.workspace.getConfiguration('aurix');
        const apiEndpoint = config.get<string>('apiEndpoint') || 'https://major-project-yo0n.onrender.com';
        const pollUrl = `${apiEndpoint}/api/scans/${scanId}`;

        return new Promise((resolve, reject) => {
            const interval = setInterval(async () => {
                try {
                    const response = await axios.get(pollUrl, {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });

                    const status = response.data.status;
                    if (status === 'COMPLETED') {
                        clearInterval(interval);
                        resolve(response.data.findings);
                    } else if (status === 'FAILED') {
                        clearInterval(interval);
                        reject(new Error('AI Engine failed to process the scan.'));
                    } else {
                        // PENDING or SCANNING
                        onUpdate(`AI Engine Status: ${status}...`);
                    }
                } catch (error) {
                    console.error('Polling error:', error);
                    // Don't clear interval on network errors, might just be a temporary blip
                }
            }, 5000);
        });
    }
}
