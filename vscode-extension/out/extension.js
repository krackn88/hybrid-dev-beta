"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.deactivate = exports.activate = void 0;
const vscode = require("vscode");
function activate(context) {
    console.log('Hybrid Extension is now active!');
    // Register hello world command
    let helloCmd = vscode.commands.registerCommand('hybrid.helloWorld', () => {
        vscode.window.showInformationMessage('Hello from Hybrid Extension!');
    });
    context.subscriptions.push(helloCmd);
    // Register run tests command
    let runTestsCmd = vscode.commands.registerCommand('hybrid.runTests', () => {
        vscode.window.showInformationMessage('Running Hybrid Tests...');
    });
    context.subscriptions.push(runTestsCmd);
    // Register build project command
    let buildCmd = vscode.commands.registerCommand('hybrid.buildProject', () => {
        vscode.window.showInformationMessage('Building Hybrid Project...');
    });
    context.subscriptions.push(buildCmd);
}
exports.activate = activate;
function deactivate() { }
exports.deactivate = deactivate;
//# sourceMappingURL=extension.js.map