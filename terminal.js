document.addEventListener("DOMContentLoaded", function() {
  var terminal = new Terminal();
  terminal.open(document.getElementById("terminal"));
  terminal.write('Welcome to the Hybrid UI Workbench Terminal!\r\n');
});
