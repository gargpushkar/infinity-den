document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-bs-toggle='tooltip']").forEach((element) => {
    new bootstrap.Tooltip(element);
  });

  document.querySelectorAll("[data-newsletter-form]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      event.preventDefault();

      const message = form.querySelector("[data-newsletter-message]");
      if (!message) {
        return;
      }

      message.classList.remove("is-success", "is-error");

      if (!form.checkValidity()) {
        form.reportValidity();
        message.textContent = "Enter a valid email to join the briefing.";
        message.classList.add("is-error");
        return;
      }

      message.textContent = "You're on the list. Watch for the next briefing.";
      message.classList.add("is-success");
      form.reset();
    });
  });
});
