document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const loginToggle = document.getElementById("login-toggle");
  const loginModal = document.getElementById("login-modal");
  const closeLogin = document.getElementById("close-login");
  const loginForm = document.getElementById("login-form");
  const userStatus = document.getElementById("user-status");

  const tokenKey = "mergington-auth-token";

  function getToken() {
    return localStorage.getItem(tokenKey);
  }

  function setToken(token) {
    if (token) {
      localStorage.setItem(tokenKey, token);
    } else {
      localStorage.removeItem(tokenKey);
    }
  }

  function getAuthHeaders() {
    const token = getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async function refreshAuthState() {
    const response = await fetch("/auth/status", { headers: getAuthHeaders() });
    const data = await response.json();

    if (data.authenticated) {
      loginToggle.textContent = "Log Out";
      userStatus.textContent = `Logged in as ${data.username} (${data.role})`;
      userStatus.classList.remove("hidden");
    } else {
      loginToggle.textContent = "Teacher Login";
      userStatus.textContent = "";
      userStatus.classList.add("hidden");
    }

    return data;
  }

  function showMessage(text, type = "success") {
    messageDiv.textContent = text;
    messageDiv.className = type;
    messageDiv.classList.remove("hidden");

    setTimeout(() => {
      messageDiv.classList.add("hidden");
    }, 5000);
  }

  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      const activities = await response.json();

      activitiesList.innerHTML = "";
      activitySelect.innerHTML = '<option value="">-- Select an activity --</option>';

      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft = details.max_participants - details.participants.length;

        const authState = getToken() ? { authenticated: true } : { authenticated: false };
        const canRemove = authState.authenticated && localStorage.getItem("mergington-role") === "teacher";

        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                  .map((email) => {
                    const removeButton = canRemove
                      ? `<button class="delete-btn" data-activity="${name}" data-email="${email}">❌</button>`
                      : "";
                    return `<li><span class="participant-email">${email}</span>${removeButton}</li>`;
                  })
                  .join("")}
              </ul>
            </div>`
            : `<p><em>No participants yet</em></p>`;

        activityCard.innerHTML = `
          <h4>${name}</h4>
          <p>${details.description}</p>
          <p><strong>Schedule:</strong> ${details.schedule}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">
            ${participantsHTML}
          </div>
        `;

        activitiesList.appendChild(activityCard);

        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.innerHTML = "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  async function handleUnregister(event) {
    const button = event.target;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
          headers: getAuthHeaders(),
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");
        fetchActivities();
      } else {
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage("Failed to unregister. Please try again.", "error");
      console.error("Error unregistering:", error);
    }
  }

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/signup?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
          headers: getAuthHeaders(),
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");
        signupForm.reset();
        fetchActivities();
      } else {
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage("Failed to sign up. Please try again.", "error");
      console.error("Error signing up:", error);
    }
  });

  loginToggle.addEventListener("click", async () => {
    const token = getToken();
    if (token) {
      await fetch("/logout", {
        method: "POST",
        headers: getAuthHeaders(),
      });
      setToken(null);
      localStorage.removeItem("mergington-role");
      await refreshAuthState();
      fetchActivities();
      return;
    }

    loginModal.classList.remove("hidden");
  });

  closeLogin.addEventListener("click", () => {
    loginModal.classList.add("hidden");
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const username = document.getElementById("login-username").value;
    const password = document.getElementById("login-password").value;

    try {
      const response = await fetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "Invalid login");
      }

      setToken(result.token);
      localStorage.setItem("mergington-role", result.role);
      loginForm.reset();
      loginModal.classList.add("hidden");
      await refreshAuthState();
      fetchActivities();
      showMessage(`Logged in as ${result.username}`, "success");
    } catch (error) {
      showMessage(error.message || "Login failed.", "error");
    }
  });

  refreshAuthState();
  fetchActivities();
});
