import * as vscode from 'vscode';

export class AurixActionProvider implements vscode.TreeDataProvider<ActionItem> {
    
    getTreeItem(element: ActionItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: ActionItem): Thenable<ActionItem[]> {
        if (element) {
            return Promise.resolve([]);
        } else {
            return Promise.resolve([
                new ActionItem('🔑 Login to AURIX', 'Authenticate your VS Code extension.', 'aurix.login', new vscode.ThemeIcon('account')),
                new ActionItem('🚀 Scan Workspace', 'Zip and send your local code to the AI Engine.', 'aurix.scanWorkspace', new vscode.ThemeIcon('play-circle')),
                new ActionItem('🐛 Run Mock Scan (Offline)', 'Test the UI without backend.', 'aurix.mockScan', new vscode.ThemeIcon('beaker'))
            ]);
        }
    }
}

class ActionItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        private readonly desc: string,
        public readonly commandId: string,
        public readonly icon: vscode.ThemeIcon
    ) {
        super(label, vscode.TreeItemCollapsibleState.None);
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
