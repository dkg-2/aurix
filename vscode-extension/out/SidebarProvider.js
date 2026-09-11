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
exports.AurixActionProvider = void 0;
const vscode = __importStar(require("vscode"));
class AurixActionProvider {
    getTreeItem(element) {
        return element;
    }
    getChildren(element) {
        if (element) {
            return Promise.resolve([]);
        }
        else {
            return Promise.resolve([
                new ActionItem('🔑 Login to AURIX', 'Authenticate your VS Code extension.', 'aurix.login', new vscode.ThemeIcon('account')),
                new ActionItem('🚀 Scan Workspace', 'Zip and send your local code to the AI Engine.', 'aurix.scanWorkspace', new vscode.ThemeIcon('play-circle')),
                new ActionItem('🐛 Run Mock Scan (Offline)', 'Test the UI without backend.', 'aurix.mockScan', new vscode.ThemeIcon('beaker'))
            ]);
        }
    }
}
exports.AurixActionProvider = AurixActionProvider;
class ActionItem extends vscode.TreeItem {
    label;
    desc;
    commandId;
    icon;
    constructor(label, desc, commandId, icon) {
        super(label, vscode.TreeItemCollapsibleState.None);
        this.label = label;
        this.desc = desc;
        this.commandId = commandId;
        this.icon = icon;
        this.tooltip = this.desc;
        this.description = this.desc;
        this.iconPath = icon;
        // Make the item clickable
        this.command = {
            command: this.commandId,
            title: this.label
        };
    }
}
//# sourceMappingURL=SidebarProvider.js.map