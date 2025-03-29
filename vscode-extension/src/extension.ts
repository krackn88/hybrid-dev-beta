import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {
  console.log('Hybrid Extension is now active!');

  // Register the hello world command
  let helloWorldCommand = vscode.commands.registerCommand('hybrid.helloWorld', () => {
    vscode.window.showInformationMessage('Hello World from Hybrid Extension!');
  });
  context.subscriptions.push(helloWorldCommand);

  // Register run tests command
  let runTestsCommand = vscode.commands.registerCommand('hybrid.runTests', () => {
    vscode.window.showInformationMessage('Running Hybrid Tests...');
    // Implement actual test runner logic here
  });
  context.subscriptions.push(runTestsCommand);

  // Register build project command
  let buildProjectCommand = vscode.commands.registerCommand('hybrid.buildProject', () => {
    vscode.window.showInformationMessage('Building Hybrid Project...');
    // Implement actual build logic here
  });
  context.subscriptions.push(buildProjectCommand);

  // Add Status Bar Information
  const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusBarItem.command = 'hybrid.showStatus';
  statusBarItem.text = 'Hybrid Status';
  statusBarItem.show();
  context.subscriptions.push(statusBarItem);

  // Register show status command
  let showStatusCommand = vscode.commands.registerCommand('hybrid.showStatus', () => {
    vscode.window.showInformationMessage('Hybrid Extension is active and running!');
  });
  context.subscriptions.push(showStatusCommand);

  // Register sidebar provider
  const sidebarProvider = new SidebarProvider(context.extensionUri);
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(SidebarProvider.viewType, sidebarProvider)
  );
}

export function deactivate() {}

class SidebarProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'hybrid.sidebar';
  private _view?: vscode.WebviewView;

  constructor(private readonly _extensionUri: vscode.Uri) {}

  public resolveWebviewView(
    webviewView: vscode.WebviewView,
    context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ) {
    this._view = webviewView;

    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [this._extensionUri]
    };

    webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);
    
    // Handle messages from the webview
    webviewView.webview.onDidReceiveMessage(
      message => {
        switch (message.command) {
          case 'runTests':
            vscode.commands.executeCommand('hybrid.runTests');
            return;
          case 'buildProject':
            vscode.commands.executeCommand('hybrid.buildProject');
            return;
          case 'showStatus':
            vscode.commands.executeCommand('hybrid.showStatus');
            return;
        }
      },
      undefined,
      // Use extension context instead of webviewView context for subscriptions
      context.subscriptions
    );
  }

  private _getHtmlForWebview(webview: vscode.Webview): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hybrid Sidebar</title>
    <style>
        body {
            padding: 10px;
            font-family: var(--vscode-font-family);
            color: var(--vscode-foreground);
            background-color: var(--vscode-editor-background);
        }
        button {
            display: block;
            width: 100%;
            padding: 8px;
            margin: 5px 0;
            background-color: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            cursor: pointer;
        }
        button:hover {
            background-color: var(--vscode-button-hoverBackground);
        }
        h3 {
            margin-top: 0;
        }
    </style>
</head>
<body>
    <h3>Hybrid Controls</h3>
    
    <button id="runTestsBtn">Run Tests</button>
    <button id="buildProjectBtn">Build Project</button>
    <button id="showStatusBtn">Show Status</button>
    
    <script>
        const vscode = acquireVsCodeApi();
        
        document.getElementById('runTestsBtn').addEventListener('click', () => {
            vscode.postMessage({ command: 'runTests' });
        });
        
        document.getElementById('buildProjectBtn').addEventListener('click', () => {
            vscode.postMessage({ command: 'buildProject' });
        });
        
        document.getElementById('showStatusBtn').addEventListener('click', () => {
            vscode.postMessage({ command: 'showStatus' });
        });
    </script>
</body>
</html>`;
  }
}
