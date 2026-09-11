import * as vscode from 'vscode';

export class AuthManager {
    private secretStorage: vscode.SecretStorage;

    constructor(context: vscode.ExtensionContext) {
        this.secretStorage = context.secrets;
    }

    public async login() {
        // Pop up an input box at the top center of VS Code
        const token = await vscode.window.showInputBox({
            prompt: 'Enter your AURIX Authentication Token',
            placeHolder: 'aurix-dev-token',
            password: true, // Hides the characters as they type
            ignoreFocusOut: true
        });

        if (!token) {
            vscode.window.showWarningMessage('AURIX Login Cancelled.');
            return;
        }

        // Securely store the token using VS Code's encrypted keychain
        await this.secretStorage.store('aurix_token', token);
        vscode.window.showInformationMessage('✅ Successfully logged into AURIX!');
    }

    public async getToken(): Promise<string | undefined> {
        return await this.secretStorage.get('aurix_token');
    }

    public async logout() {
        await this.secretStorage.delete('aurix_token');
        vscode.window.showInformationMessage('Logged out of AURIX.');
    }
}
