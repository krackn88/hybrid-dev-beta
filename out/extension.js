"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.deactivate = exports.activate = void 0;
const vscode = require("vscode");
function activate(context) {
    console.log('Congratulations, your extension "hybrid-extension" is now active!');
    let disposable = vscode.commands.registerCommand('hybrid.helloWorld', () => {
        vscode.window.showInformationMessage('Hello World from Hybrid Extension!');
    });
    context.subscriptions.push(disposable);
    // Add Sidebar Panel
    const sidebarProvider = new SidebarProvider(context.extensionUri);
    context.subscriptions.push(vscode.window.registerWebviewViewProvider(SidebarProvider.viewType, sidebarProvider));
    // Add Command Palette Integration
    context.subscriptions.push(vscode.commands.registerCommand('hybrid.runTests', () => {
        vscode.window.showInformationMessage('Running Tests...');
    }));
    context.subscriptions.push(vscode.commands.registerCommand('hybrid.buildProject', () => {
        vscode.window.showInformationMessage('Building Project...');
    }));
    // Add Status Bar Information
    const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.command = 'hybrid.showStatus';
    statusBarItem.text = 'Hybrid Status';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);
    context.subscriptions.push(vscode.commands.registerCommand('hybrid.showStatus', () => {
        vscode.window.showInformationMessage('Hybrid Extension is active!');
    }));
    // Add Editor Decorations
    const decorationType = vscode.window.createTextEditorDecorationType({
        backgroundColor: 'rgba(255,0,0,0.3)'
    });
    const activeEditor = vscode.window.activeTextEditor;
    if (activeEditor) {
        const range = new vscode.Range(new vscode.Position(0, 0), new vscode.Position(0, 10));
        activeEditor.setDecorations(decorationType, [range]);
    }
}
exports.activate = activate;
function deactivate() { }
exports.deactivate = deactivate;
class SidebarProvider {
    constructor(_extensionUri) {
        this._extensionUri = _extensionUri;
    }
    resolveWebviewView(webviewView, context, _token) {
        this._view = webviewView;
        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri]
        };
        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);
    }
    _getHtmlForWebview(webview) {
        const nonce = getNonce();
        return `<!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Hybrid Sidebar</title>
      </head>
      <body>
        <h1>Hello from the Sidebar!</h1>
      </body>
      </html>`;
    }
}
SidebarProvider.viewType = 'hybrid.sidebar';
function getNonce() {
    let text = '';
    const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    for (let i = 0; i < 32; i++) {
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    return text;
}
//# sourceMappingURL=extension.js.map