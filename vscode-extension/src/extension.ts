import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {
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

export function deactivate() {}
