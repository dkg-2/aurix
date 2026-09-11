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
exports.AuthManager = void 0;
const vscode = __importStar(require("vscode"));
class AuthManager {
    secretStorage;
    constructor(context) {
        this.secretStorage = context.secrets;
    }
    async login() {
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
    async getToken() {
        return await this.secretStorage.get('aurix_token');
    }
    async logout() {
        await this.secretStorage.delete('aurix_token');
        vscode.window.showInformationMessage('Logged out of AURIX.');
    }
}
exports.AuthManager = AuthManager;
//# sourceMappingURL=AuthManager.js.map