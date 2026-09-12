import * as vscode from 'vscode';
import { createClient, SupabaseClient, Session } from '@supabase/supabase-js';

const SUPABASE_URL = 'https://zxntvdrqokmgkbgydmzr.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp4bnR2ZHJxb2ttZ2tiZ3lkbXpyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ1NDMxMTIsImV4cCI6MjEwMDExOTExMn0.s6PBTBvtJpjkM9rGlVWsJu6b8r2M4d0aqRRzf0KjmAs';

export class AuthManager {
    private secretStorage: vscode.SecretStorage;
    private supabase: SupabaseClient;
    private _session: Session | null = null;

    constructor(context: vscode.ExtensionContext) {
        this.secretStorage = context.secrets;
        this.supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
            auth: {
                persistSession: false, // We handle persistence ourselves via SecretStorage
                autoRefreshToken: false
            }
        });
    }

    /**
     * Restore the session from secure storage on extension startup.
     */
    public async restoreSession(): Promise<boolean> {
        try {
            const stored = await this.secretStorage.get('aurix_session');
            if (!stored) { return false; }

            const { refresh_token } = JSON.parse(stored);
            if (!refresh_token) { return false; }

            const { data, error } = await this.supabase.auth.refreshSession({ refresh_token });
            if (error || !data.session) { return false; }

            this._session = data.session;
            await this._persistSession(data.session);
            return true;
        } catch {
            return false;
        }
    }

    /**
     * Shows a quick-pick menu to let the user choose Login or Sign Up.
     */
    public async login(): Promise<boolean> {
        const choice = await vscode.window.showQuickPick(
            ['Login with existing account', 'Create a new account'],
            { placeHolder: 'AURIX: How would you like to continue?', ignoreFocusOut: true }
        );

        if (!choice) { return false; }

        if (choice === 'Login with existing account') {
            return await this._loginFlow();
        } else {
            return await this._signupFlow();
        }
    }

    private async _loginFlow(): Promise<boolean> {
        const email = await vscode.window.showInputBox({
            prompt: 'Enter your AURIX account email',
            placeHolder: 'you@example.com',
            ignoreFocusOut: true,
            validateInput: v => v && v.includes('@') ? undefined : 'Please enter a valid email'
        });
        if (!email) { return false; }

        const password = await vscode.window.showInputBox({
            prompt: 'Enter your password',
            placeHolder: '••••••••',
            password: true,
            ignoreFocusOut: true
        });
        if (!password) { return false; }

        return await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: 'AURIX: Logging in...',
            cancellable: false
        }, async () => {
            const { data, error } = await this.supabase.auth.signInWithPassword({ email, password });
            if (error || !data.session) {
                vscode.window.showErrorMessage(`AURIX Login Failed: ${error?.message || 'Unknown error'}`);
                return false;
            }
            this._session = data.session;
            await this._persistSession(data.session);
            vscode.window.showInformationMessage(`AURIX: Welcome back, ${data.user?.email}!`);
            return true;
        });
    }

    private async _signupFlow(): Promise<boolean> {
        const email = await vscode.window.showInputBox({
            prompt: 'Enter your email address for your new AURIX account',
            placeHolder: 'you@example.com',
            ignoreFocusOut: true,
            validateInput: v => v && v.includes('@') ? undefined : 'Please enter a valid email'
        });
        if (!email) { return false; }

        const password = await vscode.window.showInputBox({
            prompt: 'Create a password (min 6 characters)',
            placeHolder: '••••••••',
            password: true,
            ignoreFocusOut: true,
            validateInput: v => v && v.length >= 6 ? undefined : 'Password must be at least 6 characters'
        });
        if (!password) { return false; }

        const confirmPassword = await vscode.window.showInputBox({
            prompt: 'Confirm your password',
            placeHolder: '••••••••',
            password: true,
            ignoreFocusOut: true
        });
        if (confirmPassword !== password) {
            vscode.window.showErrorMessage('AURIX: Passwords do not match!');
            return false;
        }

        return await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: 'AURIX: Creating your account...',
            cancellable: false
        }, async () => {
            const { data, error } = await this.supabase.auth.signUp({ email, password });
            if (error) {
                vscode.window.showErrorMessage(`AURIX Sign Up Failed: ${error.message}`);
                return false;
            }
            if (!data.session) {
                // Email confirmation required
                vscode.window.showInformationMessage(
                    `AURIX: Account created! Check ${email} for a confirmation link, then login.`
                );
                return false;
            }
            this._session = data.session;
            await this._persistSession(data.session);
            vscode.window.showInformationMessage(`AURIX: Account created! Welcome, ${data.user?.email}!`);
            return true;
        });
    }

    /**
     * Returns the current JWT access token for API calls.
     */
    public async getToken(): Promise<string | undefined> {
        // Check if we have a valid in-memory session
        if (this._session) {
            const expiresAt = this._session.expires_at || 0;
            const nowSeconds = Math.floor(Date.now() / 1000);

            // If token expires within 60 seconds, refresh it
            if (expiresAt - nowSeconds < 60) {
                const refreshed = await this.restoreSession();
                if (!refreshed) {
                    this._session = null;
                    return undefined;
                }
            }
            return this._session.access_token;
        }
        return undefined;
    }

    /**
     * Returns the current user's info (email, id, etc.)
     */
    public async getCurrentUser(): Promise<{ id: string; email: string } | null> {
        const token = await this.getToken();
        if (!token || !this._session?.user) { return null; }
        return {
            id: this._session.user.id,
            email: this._session.user.email || ''
        };
    }

    /**
     * Returns true if the user is logged in with a valid session.
     */
    public async isLoggedIn(): Promise<boolean> {
        const token = await this.getToken();
        return !!token;
    }

    /**
     * Logs the user out and clears all stored credentials.
     */
    public async logout(): Promise<void> {
        await this.supabase.auth.signOut();
        this._session = null;
        await this.secretStorage.delete('aurix_session');
        vscode.window.showInformationMessage('AURIX: Logged out successfully.');
    }

    private async _persistSession(session: Session): Promise<void> {
        await this.secretStorage.store('aurix_session', JSON.stringify({
            access_token: session.access_token,
            refresh_token: session.refresh_token,
            expires_at: session.expires_at
        }));
    }
}
