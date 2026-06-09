const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

if (!prefersReducedMotion) {
  document.documentElement.classList.add("motion-ready");
}

document.addEventListener("DOMContentLoaded", () => {
  if (window.bootstrap?.Tooltip) {
    document.querySelectorAll("[data-bs-toggle='tooltip']").forEach((element) => {
      new bootstrap.Tooltip(element);
    });
  }

  const revealBlocks = document.querySelectorAll("[data-reveal]");

  const prepareRevealChildren = (block) => {
    block.querySelectorAll("[data-reveal-child]").forEach((child, index) => {
      child.style.setProperty("--reveal-delay", `${Math.min(index * 85, 425)}ms`);
    });
  };

  const revealBlock = (block) => {
    prepareRevealChildren(block);
    block.classList.add("is-visible");
  };

  if (prefersReducedMotion || !("IntersectionObserver" in window)) {
    revealBlocks.forEach(revealBlock);
  } else {
    const revealObserver = new IntersectionObserver(
      (entries, observer) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) {
            return;
          }

          revealBlock(entry.target);
          observer.unobserve(entry.target);
        });
      },
      {
        rootMargin: "0px 0px -12% 0px",
        threshold: 0.16,
      },
    );

    revealBlocks.forEach((block) => {
      prepareRevealChildren(block);
      revealObserver.observe(block);
    });
  }

  const briefingRows = Array.from(document.querySelectorAll("[data-briefing-row]"));

  if (briefingRows.length > 1) {
    let activeBriefingIndex = Math.max(
      0,
      briefingRows.findIndex((row) => row.classList.contains("active")),
    );

    const setActiveBriefingRow = (nextIndex) => {
      briefingRows.forEach((row, index) => {
        const isActive = index === nextIndex;
        row.classList.toggle("active", isActive);
        row.classList.toggle("is-active", isActive);
      });
    };

    setActiveBriefingRow(activeBriefingIndex);

    if (!prefersReducedMotion) {
      window.setInterval(() => {
        activeBriefingIndex = (activeBriefingIndex + 1) % briefingRows.length;
        setActiveBriefingRow(activeBriefingIndex);
      }, 2600);
    }
  }

  document.querySelectorAll("[data-newsletter-form]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      const message = form.querySelector("[data-newsletter-message]");
      const emailInput = form.querySelector("input[name='email']");
      const submitButton = form.querySelector("[type='submit']");
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

      const email = emailInput?.value?.trim();
      if (!email) {
        message.textContent = "Enter a valid email to join the briefing.";
        message.classList.add("is-error");
        return;
      }

      if (submitButton) {
        submitButton.disabled = true;
        submitButton.setAttribute("aria-busy", "true");
      }
      message.textContent = "Subscribing...";

      try {
        const response = await fetch(form.action, {
          method: "POST",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ email }),
        });
        const payload = await response.json().catch(() => ({}));

        if (response.ok) {
          message.textContent = "You're on the list. Watch for the next briefing.";
          message.classList.add("is-success");
          form.reset();
          return;
        }

        if (response.status === 409) {
          message.textContent = "You're already on the list.";
          message.classList.add("is-success");
          return;
        }

        message.textContent =
          payload?.error?.message || "We could not save that email right now.";
        message.classList.add("is-error");
      } catch (error) {
        message.textContent = "Connection issue. Try again in a moment.";
        message.classList.add("is-error");
      } finally {
        if (submitButton) {
          submitButton.disabled = false;
          submitButton.removeAttribute("aria-busy");
        }
      }
    });
  });

  document.querySelectorAll("[data-submission-form]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      const message = form.querySelector("[data-submission-message]");
      const submitButton = form.querySelector("[type='submit']");
      if (!message) {
        return;
      }

      message.classList.remove("is-success", "is-error");

      if (!form.checkValidity()) {
        form.reportValidity();
        message.textContent = "Complete each field before sending your pitch.";
        message.classList.add("is-error");
        return;
      }

      const formData = new FormData(form);
      const payload = {
        name: String(formData.get("name") || "").trim(),
        email: String(formData.get("email") || "").trim(),
        topic: String(formData.get("topic") || "").trim(),
        content_idea: String(formData.get("content_idea") || "").trim(),
      };

      if (submitButton) {
        submitButton.disabled = true;
        submitButton.setAttribute("aria-busy", "true");
      }
      message.textContent = "Sending pitch...";

      try {
        const response = await fetch(form.action, {
          method: "POST",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });
        const responsePayload = await response.json().catch(() => ({}));

        if (response.ok) {
          message.textContent = "Pitch received. We'll review it with the next editorial batch.";
          message.classList.add("is-success");
          form.reset();
          return;
        }

        message.textContent =
          responsePayload?.error?.message || "We could not save that pitch right now.";
        message.classList.add("is-error");
      } catch (error) {
        message.textContent = "Connection issue. Try again in a moment.";
        message.classList.add("is-error");
      } finally {
        if (submitButton) {
          submitButton.disabled = false;
          submitButton.removeAttribute("aria-busy");
        }
      }
    });
  });

  document.querySelectorAll("[data-admin-login-form]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      const message = form.querySelector("[data-admin-login-message]");
      const submitButton = form.querySelector("[type='submit']");
      if (!message) {
        return;
      }

      message.classList.remove("is-success", "is-error");

      if (!form.checkValidity()) {
        form.reportValidity();
        message.textContent = "Enter your username and password.";
        message.classList.add("is-error");
        return;
      }

      const formData = new FormData(form);
      const payload = {
        username: String(formData.get("username") || "").trim(),
        password: String(formData.get("password") || ""),
      };

      if (submitButton) {
        submitButton.disabled = true;
        submitButton.setAttribute("aria-busy", "true");
      }
      message.textContent = "Signing in...";

      try {
        const response = await fetch(form.action, {
          method: "POST",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });
        const responsePayload = await response.json().catch(() => ({}));

        if (response.ok) {
          message.textContent = "Access granted. Opening admin.";
          message.classList.add("is-success");
          window.location.assign("/admin");
          return;
        }

        message.textContent =
          responsePayload?.error?.message || "Sign in failed.";
        message.classList.add("is-error");
      } catch (error) {
        message.textContent = "Connection issue. Try again in a moment.";
        message.classList.add("is-error");
      } finally {
        if (submitButton) {
          submitButton.disabled = false;
          submitButton.removeAttribute("aria-busy");
        }
      }
    });
  });

  const adminJsonRequest = async (url, options = {}) => {
    const response = await fetch(url, {
      method: options.method || "GET",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: options.body ? JSON.stringify(options.body) : undefined,
    });
    const payload = await response.json().catch(() => ({}));

    if (!response.ok) {
      const message =
        payload?.error?.message || payload?.detail || "Admin action failed.";
      throw new Error(message);
    }

    return payload;
  };

  const setAdminMessage = (element, text, type = "neutral") => {
    if (!element) {
      return;
    }

    element.classList.remove("is-success", "is-error");
    if (type === "success") {
      element.classList.add("is-success");
    }
    if (type === "error") {
      element.classList.add("is-error");
    }
    element.textContent = text;
  };

  const slugify = (value) =>
    String(value || "")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .replace(/-{2,}/g, "-");

  document.querySelectorAll("[data-admin-slug-source]").forEach((source) => {
    const form = source.closest("form");
    const target = form?.querySelector("[data-admin-slug-target]");
    if (!target) {
      return;
    }

    source.addEventListener("input", () => {
      if (target.dataset.slugTouched === "true") {
        return;
      }

      target.value = slugify(source.value);
    });

    target.addEventListener("input", () => {
      target.dataset.slugTouched = "true";
      target.value = slugify(target.value);
    });
  });

  document.querySelectorAll("[data-admin-sidebar-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      document.body.classList.toggle("admin-nav-open");
    });
  });

  document.querySelectorAll("[data-admin-logout-form]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      await fetch(form.action, { method: "POST" }).catch(() => null);
      window.location.assign("/admin/login");
    });
  });

  document.querySelectorAll("[data-admin-article-editor]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      const message = form.querySelector("[data-admin-form-message]");
      const submitButton = form.querySelector("[type='submit']");
      if (!form.checkValidity()) {
        form.reportValidity();
        setAdminMessage(message, "Complete the required article fields.", "error");
        return;
      }

      const formData = new FormData(form);
      const status = String(formData.get("status") || "draft");
      const payload = {
        title: String(formData.get("title") || "").trim(),
        slug: slugify(formData.get("slug")),
        excerpt: String(formData.get("excerpt") || "").trim(),
        content: String(formData.get("content") || "").trim(),
        cover_image: String(formData.get("cover_image") || "").trim() || null,
        author: String(formData.get("author") || "").trim(),
        category_id: String(formData.get("category_id") || "").trim() || null,
        tags: String(formData.get("tags") || "")
          .split(",")
          .map((tag) => tag.trim())
          .filter(Boolean),
        is_featured: formData.get("is_featured") === "true",
        status,
        seo_title: String(formData.get("seo_title") || "").trim() || null,
        seo_description:
          String(formData.get("seo_description") || "").trim() || null,
      };

      if (status === "published") {
        payload.published_at = new Date().toISOString();
      }
      if (status === "draft") {
        payload.published_at = null;
      }

      if (submitButton) {
        submitButton.disabled = true;
      }
      setAdminMessage(message, "Saving article...");

      try {
        const method = form.dataset.editorMode === "update" ? "PATCH" : "POST";
        const article = await adminJsonRequest(form.action, { method, body: payload });
        setAdminMessage(message, "Article saved.", "success");

        if (form.dataset.editorMode !== "update") {
          window.location.assign(`/admin/articles/${article.id}/edit`);
        }
      } catch (error) {
        setAdminMessage(message, error.message, "error");
      } finally {
        if (submitButton) {
          submitButton.disabled = false;
        }
      }
    });
  });

  document.querySelectorAll("[data-admin-article-status-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      const articleId = button.getAttribute("data-article-id");
      const statusAction = button.getAttribute("data-status-action");
      const row = button.closest("[data-admin-article-row]");
      const statusLabel = row?.querySelector("[data-admin-article-status]");
      const message = document.querySelector("[data-admin-table-message]");
      if (!articleId || !statusAction) {
        return;
      }

      button.disabled = true;
      try {
        const article = await adminJsonRequest(
          `/api/admin/articles/${articleId}/${statusAction}`,
          { method: "PATCH" },
        );
        if (statusLabel) {
          statusLabel.textContent = article.status;
        }
        setAdminMessage(message, `Article moved to ${article.status}.`, "success");
      } catch (error) {
        setAdminMessage(message, error.message, "error");
      } finally {
        button.disabled = false;
      }
    });
  });

  document.querySelectorAll("[data-admin-article-feature]").forEach((button) => {
    button.addEventListener("click", async () => {
      const articleId = button.getAttribute("data-article-id");
      const nextFeatured = button.getAttribute("data-featured") !== "true";
      const message = document.querySelector("[data-admin-table-message]");
      if (!articleId) {
        return;
      }

      button.disabled = true;
      try {
        const article = await adminJsonRequest(
          `/api/admin/articles/${articleId}/feature`,
          {
            method: "PATCH",
            body: { is_featured: nextFeatured },
          },
        );
        button.dataset.featured = article.is_featured ? "true" : "false";
        button.textContent = article.is_featured ? "On" : "Off";
        setAdminMessage(message, "Featured state updated.", "success");
      } catch (error) {
        setAdminMessage(message, error.message, "error");
      } finally {
        button.disabled = false;
      }
    });
  });

  document.querySelectorAll("[data-admin-delete-resource]").forEach((button) => {
    button.addEventListener("click", async () => {
      const deleteUrl = button.getAttribute("data-delete-url");
      const label = button.getAttribute("data-delete-label") || "this item";
      const message =
        document.querySelector("[data-admin-table-message]") ||
        document.querySelector("[data-admin-form-message]");
      if (!deleteUrl || !window.confirm(`Delete ${label}?`)) {
        return;
      }

      button.disabled = true;
      try {
        await fetch(deleteUrl, { method: "DELETE" }).then((response) => {
          if (!response.ok) {
            throw new Error("Delete failed.");
          }
        });
        button.closest("tr, [data-admin-category-row]")?.remove();
        setAdminMessage(message, "Deleted.", "success");
      } catch (error) {
        setAdminMessage(message, error.message, "error");
      } finally {
        button.disabled = false;
      }
    });
  });

  document.querySelectorAll("[data-admin-category-form]").forEach((form) => {
    const heading = form.querySelector("[data-admin-category-heading]");
    const resetButton = form.querySelector("[data-admin-category-reset]");
    const message = form.querySelector("[data-admin-form-message]");
    const idInput = form.querySelector("input[name='category_id']");

    const resetForm = () => {
      form.reset();
      if (idInput) {
        idInput.value = "";
      }
      const slugTarget = form.querySelector("[data-admin-slug-target]");
      if (slugTarget) {
        delete slugTarget.dataset.slugTouched;
      }
      if (heading) {
        heading.textContent = "Create category";
      }
      setAdminMessage(message, "Ready to save.");
    };

    resetButton?.addEventListener("click", resetForm);

    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      if (!form.checkValidity()) {
        form.reportValidity();
        setAdminMessage(message, "Complete the required category fields.", "error");
        return;
      }

      const formData = new FormData(form);
      const categoryId = String(formData.get("category_id") || "");
      const payload = {
        name: String(formData.get("name") || "").trim(),
        slug: slugify(formData.get("slug")),
        description: String(formData.get("description") || "").trim() || null,
        image: String(formData.get("image") || "").trim() || null,
      };
      const submitButton = form.querySelector("[type='submit']");

      if (submitButton) {
        submitButton.disabled = true;
      }
      setAdminMessage(message, "Saving category...");

      try {
        await adminJsonRequest(
          categoryId ? `/api/categories/${categoryId}` : "/api/categories",
          {
            method: categoryId ? "PATCH" : "POST",
            body: payload,
          },
        );
        setAdminMessage(message, "Category saved.", "success");
        window.setTimeout(() => window.location.reload(), 450);
      } catch (error) {
        setAdminMessage(message, error.message, "error");
      } finally {
        if (submitButton) {
          submitButton.disabled = false;
        }
      }
    });
  });

  document.querySelectorAll("[data-admin-edit-category]").forEach((button) => {
    button.addEventListener("click", () => {
      const row = button.closest("[data-admin-category-row]");
      const form = document.querySelector("[data-admin-category-form]");
      if (!row || !form) {
        return;
      }

      form.querySelector("input[name='category_id']").value =
        row.getAttribute("data-category-id") || "";
      form.querySelector("input[name='name']").value =
        row.getAttribute("data-category-name") || "";
      form.querySelector("input[name='slug']").value =
        row.getAttribute("data-category-slug") || "";
      form.querySelector("textarea[name='description']").value =
        row.getAttribute("data-category-description") || "";
      form.querySelector("input[name='image']").value =
        row.getAttribute("data-category-image") || "";
      form.querySelector("[data-admin-slug-target]").dataset.slugTouched = "true";
      form.querySelector("[data-admin-category-heading]").textContent =
        "Edit category";
      form.scrollIntoView({ behavior: prefersReducedMotion ? "auto" : "smooth" });
    });
  });

  document
    .querySelectorAll("[data-admin-submission-status-action]")
    .forEach((button) => {
      button.addEventListener("click", async () => {
        const submissionId = button.getAttribute("data-submission-id");
        const status = button.getAttribute("data-status");
        const card = button.closest("[data-admin-submission-card]");
        const label = card?.querySelector("[data-admin-submission-status]");
        const message = document.querySelector("[data-admin-submission-message]");
        if (!submissionId || !status) {
          return;
        }

        button.disabled = true;
        try {
          const submission = await adminJsonRequest(
            `/api/admin/submissions/${submissionId}/status`,
            {
              method: "PATCH",
              body: { status },
            },
          );
          if (label) {
            label.textContent = submission.status;
          }
          setAdminMessage(message, `Submission marked ${submission.status}.`, "success");
        } catch (error) {
          setAdminMessage(message, error.message, "error");
        } finally {
          button.disabled = false;
        }
      });
    });

  document.querySelectorAll("[data-share-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      const shareUrl = button.getAttribute("data-share-url");
      const sharePanel = button.closest(".article-share-panel");
      const status = sharePanel?.querySelector("[data-share-status]");
      if (!shareUrl || !status) {
        return;
      }

      const writeToClipboard = async () => {
        if (navigator.clipboard?.writeText) {
          await navigator.clipboard.writeText(shareUrl);
          return;
        }

        const textArea = document.createElement("textarea");
        textArea.value = shareUrl;
        textArea.setAttribute("readonly", "");
        textArea.style.position = "fixed";
        textArea.style.opacity = "0";
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand("copy");
        textArea.remove();
      };

      try {
        await writeToClipboard();
        status.textContent = "Copied";
        window.setTimeout(() => {
          status.textContent = "";
        }, 2200);
      } catch (error) {
        status.textContent = "Copy failed";
      }
    });
  });
});
