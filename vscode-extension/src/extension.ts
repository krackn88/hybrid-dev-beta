import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {
  console.log('Congratulations, your extension "hybrid-extension" is now active!');

  let disposable = vscode.commands.registerCommand('hybrid.helloWorld', () => {
    vscode.window.showInformationMessage('Hello World from Hybrid Extension!');
  });

  context.subscriptions.push(disposable);
}

export function deactivate() {}
