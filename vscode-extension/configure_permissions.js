document.addEventListener("DOMContentLoaded", function() {
  const form = document.getElementById("config-form");
  const message = document.getElementById("message");

  form.addEventListener("submit", function(event) {
    event.preventDefault();

    const user = document.getElementById("user").value;
    const role = document.getElementById("role").value;

    fetch("/update_role", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ user, role })
    })
    .then(response => response.json())
    .then(data => {
      message.textContent = data.message;
    })
    .catch(error => {
      console.error("Error:", error);
      message.textContent = "An error occurred while updating the role.";
    });
  });
});
