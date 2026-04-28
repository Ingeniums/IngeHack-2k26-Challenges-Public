const form = document.getElementById("registration-form");
const statusElement = document.getElementById("form-status");
const submitButton = form.querySelector('button[type="submit"]');

function setStatus(message, type) {
  statusElement.textContent = message;
  statusElement.className = "form-status";

  if (type) {
    statusElement.classList.add(`is-${type}`);
  }
}

function getPayload(formData) {
  return {
    firstName: formData.get("firstName")?.toString().trim() || "",
    lastName: formData.get("lastName")?.toString().trim() || "",
    email: formData.get("email")?.toString().trim() || "",
    phone: formData.get("phone")?.toString().trim() || "",
    dateOfBirth: formData.get("dateOfBirth")?.toString().trim() || "",
    address: formData.get("address")?.toString().trim() || "",
  };
}

function validatePayload(payload) {
  return Object.values(payload).every(Boolean);
}

async function submitRegistration(payload) {
  const endpoint = window.APP_CONFIG?.apiUrl;

  if (!endpoint) {
    throw new Error("Add your backend API URL in frontend/config.js.");
  }

  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const result = await response.json().catch(() => null);

  if (!response.ok || result?.ok === false) {
    throw new Error(result?.message || "Submission failed.");
  }

  return result;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setStatus("");

  const formData = new FormData(form);
  const payload = getPayload(formData);

  if (!validatePayload(payload)) {
    setStatus("Fill in every field before submitting.", "error");
    return;
  }

  submitButton.disabled = true;
  submitButton.textContent = "Submitting...";

  try {
    const result = await submitRegistration(payload);
    form.reset();
    setStatus(
      result?.message || "Registration submitted successfully.",
      "success",
    );
  } catch (error) {
    setStatus(error.message || "Submission failed. Try again.", "error");
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Submit Registration";
  }
});
