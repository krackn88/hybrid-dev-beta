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
}
exports.activate = activate;
function deactivate() { }
exports.deactivate = deactivate;
//# sourceMappingURL=extension.js.map