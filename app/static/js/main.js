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

  const getAdminCsrfToken = () =>
    document
      .querySelector("meta[name='admin-csrf-token']")
      ?.getAttribute("content") || "";

  const adminJsonRequest = async (url, options = {}) => {
    const method = options.method || "GET";
    const headers = {
      Accept: "application/json",
      "Content-Type": "application/json",
    };
    if (!["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase())) {
      const csrfToken = getAdminCsrfToken();
      if (csrfToken) {
        headers["X-CSRF-Token"] = csrfToken;
      }
    }

    const response = await fetch(url, {
      method,
      headers,
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

  const formatAdminDate = (value) => {
    if (!value) {
      return "Not recorded";
    }

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return "Not recorded";
    }

    return new Intl.DateTimeFormat("en", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(date);
  };

  const splitAdminTags = (value) =>
    String(value || "")
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean)
      .filter((tag, index, tags) => (
        tags.findIndex((candidate) => candidate.toLowerCase() === tag.toLowerCase()) ===
        index
      ));

  const escapeHtml = (value) =>
    String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");

  const renderInlineMarkdown = (value) => {
    let html = escapeHtml(value);
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/_([^_]+)_/g, "<em>$1</em>");
    html = html.replace(
      /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>',
    );
    return html;
  };

  const renderMarkdownPreview = (value) => {
    const lines = String(value || "").split(/\r?\n/);
    const html = [];
    let listItems = [];

    const flushList = () => {
      if (!listItems.length) {
        return;
      }
      html.push(`<ul>${listItems.map((item) => `<li>${item}</li>`).join("")}</ul>`);
      listItems = [];
    };

    lines.forEach((line) => {
      const trimmed = line.trim();
      if (!trimmed) {
        flushList();
        return;
      }

      if (trimmed.startsWith("- ")) {
        listItems.push(renderInlineMarkdown(trimmed.slice(2)));
        return;
      }

      flushList();
      if (trimmed.startsWith("### ")) {
        html.push(`<h3>${renderInlineMarkdown(trimmed.slice(4))}</h3>`);
        return;
      }
      if (trimmed.startsWith("## ")) {
        html.push(`<h2>${renderInlineMarkdown(trimmed.slice(3))}</h2>`);
        return;
      }
      if (trimmed.startsWith("> ")) {
        html.push(`<blockquote>${renderInlineMarkdown(trimmed.slice(2))}</blockquote>`);
        return;
      }
      html.push(`<p>${renderInlineMarkdown(trimmed)}</p>`);
    });
    flushList();

    return html.join("") || '<p class="admin-empty">Preview will appear here.</p>';
  };

  const insertMarkdown = (textarea, action) => {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const value = textarea.value;
    const selected = value.slice(start, end);
    let nextText = selected;
    let selectionOffset = 0;

    if (action === "bold") {
      nextText = `**${selected || "bold text"}**`;
      selectionOffset = selected ? nextText.length : 2;
    }
    if (action === "italic") {
      nextText = `_${selected || "italic text"}_`;
      selectionOffset = selected ? nextText.length : 1;
    }
    if (action === "link") {
      nextText = `[${selected || "link text"}](https://example.com)`;
      selectionOffset = selected ? nextText.length : 1;
    }
    if (action === "heading") {
      nextText = selected
        ? selected
            .split(/\r?\n/)
            .map((line) => `## ${line}`)
            .join("\n")
        : "## Heading";
      selectionOffset = nextText.length;
    }
    if (action === "quote") {
      nextText = selected
        ? selected
            .split(/\r?\n/)
            .map((line) => `> ${line}`)
            .join("\n")
        : "> Quote";
      selectionOffset = nextText.length;
    }
    if (action === "list") {
      nextText = selected
        ? selected
            .split(/\r?\n/)
            .map((line) => `- ${line}`)
            .join("\n")
        : "- List item";
      selectionOffset = nextText.length;
    }

    textarea.value = `${value.slice(0, start)}${nextText}${value.slice(end)}`;
    textarea.focus();
    if (selected) {
      textarea.setSelectionRange(start, start + nextText.length);
    } else {
      textarea.setSelectionRange(start + selectionOffset, start + nextText.length);
    }
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
  };

  const serializeArticleEditorDraft = (form) => {
    const data = {};
    form.querySelectorAll("input[name], textarea[name], select[name]").forEach((field) => {
      if (field.type === "checkbox") {
        data[field.name] = field.checked;
        return;
      }
      data[field.name] = field.value;
    });
    return data;
  };

  const applyArticleEditorDraft = (form, data) => {
    Object.entries(data || {}).forEach(([name, value]) => {
      const field = Array.from(form.querySelectorAll("input[name], textarea[name], select[name]"))
        .find((candidate) => candidate.name === name);
      if (!field) {
        return;
      }
      if (field.type === "checkbox") {
        field.checked = Boolean(value);
        return;
      }
      field.value = value || "";
    });
    form.dispatchEvent(new CustomEvent("admin:editor-draft-applied"));
  };

  const setupAdminValidationSummary = (form) => {
    const summary = form.querySelector("[data-admin-validation-summary]");
    const list = summary?.querySelector("ul");

    const clear = () => {
      if (!summary || !list) {
        return;
      }
      list.innerHTML = "";
      summary.hidden = true;
    };

    const show = (messages) => {
      if (!summary || !list || !messages.length) {
        return;
      }
      list.innerHTML = messages.map((message) => `<li>${escapeHtml(message)}</li>`).join("");
      summary.hidden = false;
    };

    return { clear, show };
  };

  const fieldLabel = (field) => {
    const id = field.getAttribute("id");
    if (!id) {
      return field.name || "Field";
    }
    return Array.from(document.querySelectorAll("label"))
      .find((label) => label.getAttribute("for") === id)
      ?.textContent || field.name;
  };

  const collectArticleValidationMessages = (form) => {
    const messages = [];
    form.querySelectorAll("input[name], textarea[name], select[name]").forEach((field) => {
      if (field.type === "hidden" || field.checkValidity()) {
        return;
      }

      const label = fieldLabel(field);
      if (field.validity.valueMissing) {
        messages.push(`${label} is required.`);
        return;
      }
      if (field.validity.tooShort) {
        messages.push(`${label} is too short.`);
        return;
      }
      if (field.validity.tooLong) {
        messages.push(`${label} is too long.`);
        return;
      }
      if (field.validity.patternMismatch) {
        messages.push(`${label} has an invalid format.`);
        return;
      }
      messages.push(`${label} needs attention.`);
    });

    const tags = splitAdminTags(form.querySelector("[data-admin-tags-value]")?.value);
    if (tags.length > 20) {
      messages.push("Tags must be limited to 20 items.");
    }

    return messages;
  };

  const setupAdminTagEditor = (form) => {
    const hiddenInput = form.querySelector("[data-admin-tags-value]");
    const tagInput = form.querySelector("[data-admin-tag-input]");
    const tagList = form.querySelector("[data-admin-tag-list]");
    if (!hiddenInput || !tagInput || !tagList) {
      return { sync: () => splitAdminTags(hiddenInput?.value) };
    }

    let tags = splitAdminTags(hiddenInput.value);

    const sync = () => {
      hiddenInput.value = tags.join(", ");
      hiddenInput.dispatchEvent(new Event("input", { bubbles: true }));
      return tags;
    };

    const render = () => {
      tagList.innerHTML = tags
        .map(
          (tag) => `
            <span class="admin-tag-chip">
              ${escapeHtml(tag)}
              <button type="button" data-admin-remove-tag="${escapeHtml(tag)}" aria-label="Remove ${escapeHtml(tag)}">x</button>
            </span>
          `,
        )
        .join("");
      sync();
    };

    const addTag = (value) => {
      const cleanTag = String(value || "").trim();
      if (!cleanTag || cleanTag.length > 64 || tags.length >= 20) {
        return;
      }
      if (tags.some((tag) => tag.toLowerCase() === cleanTag.toLowerCase())) {
        return;
      }
      tags.push(cleanTag);
      tagInput.value = "";
      render();
    };

    tagInput.addEventListener("keydown", (event) => {
      if (!["Enter", ","].includes(event.key)) {
        return;
      }
      event.preventDefault();
      addTag(tagInput.value);
    });

    tagInput.addEventListener("blur", () => addTag(tagInput.value));

    tagList.addEventListener("click", (event) => {
      const button = event.target.closest("[data-admin-remove-tag]");
      if (!button) {
        return;
      }
      tags = tags.filter((tag) => tag !== button.getAttribute("data-admin-remove-tag"));
      render();
    });

    form.addEventListener("admin:editor-draft-applied", () => {
      tags = splitAdminTags(hiddenInput.value);
      render();
    });

    render();
    return { sync };
  };

  const setupAdminCategorySelector = (form) => {
    const filter = form.querySelector("[data-admin-category-filter]");
    const select = form.querySelector("select[name='category_id']");
    const note = form.querySelector("[data-admin-category-note]");
    if (!select) {
      return;
    }

    const updateNote = () => {
      if (!note) {
        return;
      }
      const option = select.selectedOptions[0];
      const name = option?.getAttribute("data-category-name") || option?.textContent || "Uncategorized";
      const description = option?.getAttribute("data-category-description") || "";
      note.textContent = description ? `${name}: ${description}` : name.trim();
    };

    filter?.addEventListener("input", () => {
      const query = filter.value.trim().toLowerCase();
      Array.from(select.options).forEach((option) => {
        const text = `${option.textContent || ""} ${option.getAttribute("data-category-description") || ""}`.toLowerCase();
        option.hidden = Boolean(query) && !text.includes(query);
      });
    });

    select.addEventListener("change", updateNote);
    form.addEventListener("admin:editor-draft-applied", updateNote);
    updateNote();
  };

  const setupAdminMarkdownEditor = (form) => {
    const textarea = form.querySelector("textarea[name='content']");
    const preview = form.querySelector("[data-admin-editor-pane='preview']");
    const modeLabel = form.querySelector("[data-admin-editor-mode-label]");
    if (!textarea || !preview) {
      return;
    }

    const updatePreview = () => {
      preview.innerHTML = renderMarkdownPreview(textarea.value);
    };

    form.querySelectorAll("[data-markdown-action]").forEach((button) => {
      button.addEventListener("click", () => {
        insertMarkdown(textarea, button.getAttribute("data-markdown-action"));
        updatePreview();
      });
    });

    form.querySelectorAll("[data-admin-editor-tab]").forEach((button) => {
      button.addEventListener("click", () => {
        const nextView = button.getAttribute("data-admin-editor-tab");
        form.querySelectorAll("[data-admin-editor-tab]").forEach((tab) => {
          const isActive = tab === button;
          tab.classList.toggle("is-active", isActive);
          tab.setAttribute("aria-selected", isActive ? "true" : "false");
        });
        form.querySelectorAll("[data-admin-editor-pane]").forEach((pane) => {
          const isActive = pane.getAttribute("data-admin-editor-pane") === nextView;
          pane.classList.toggle("is-active", isActive);
          pane.hidden = !isActive;
        });
        if (modeLabel) {
          modeLabel.textContent = nextView === "preview" ? "Previewing" : "Writing";
        }
        if (nextView === "preview") {
          updatePreview();
        }
      });
    });

    textarea.addEventListener("input", updatePreview);
    form.addEventListener("admin:editor-draft-applied", updatePreview);
    updatePreview();
  };

  const setupArticleAutosave = (form) => {
    const key = form.getAttribute("data-autosave-key");
    const status = form.querySelector("[data-admin-autosave-status]");
    const restoreButton = form.querySelector("[data-admin-autosave-restore]");
    const discardButton = form.querySelector("[data-admin-autosave-discard]");
    if (!key || !window.localStorage) {
      return {
        markSaved: () => {},
        markDirty: () => {},
        isDirty: () => false,
      };
    }

    let dirty = false;
    let lastSavedSnapshot = JSON.stringify(serializeArticleEditorDraft(form));

    const setStatus = (text) => {
      if (status) {
        status.textContent = text;
      }
    };

    const storedDraft = window.localStorage.getItem(key);
    if (storedDraft) {
      restoreButton.hidden = false;
      discardButton.hidden = false;
      setStatus("Autosaved draft available");
    }

    const markDirty = () => {
      dirty = JSON.stringify(serializeArticleEditorDraft(form)) !== lastSavedSnapshot;
    };

    const saveDraft = () => {
      if (!dirty) {
        return;
      }
      const payload = {
        saved_at: new Date().toISOString(),
        fields: serializeArticleEditorDraft(form),
      };
      window.localStorage.setItem(key, JSON.stringify(payload));
      const time = new Intl.DateTimeFormat("en", {
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date());
      setStatus(`Autosaved ${time}`);
    };

    const markSaved = () => {
      dirty = false;
      lastSavedSnapshot = JSON.stringify(serializeArticleEditorDraft(form));
      window.localStorage.removeItem(key);
      restoreButton.hidden = true;
      discardButton.hidden = true;
      setStatus("Saved");
    };

    form.addEventListener("input", markDirty);
    form.addEventListener("change", markDirty);
    window.setInterval(saveDraft, 1800);

    restoreButton?.addEventListener("click", () => {
      const draft = JSON.parse(window.localStorage.getItem(key) || "{}");
      applyArticleEditorDraft(form, draft.fields || {});
      markDirty();
      setStatus("Draft restored");
    });

    discardButton?.addEventListener("click", () => {
      window.localStorage.removeItem(key);
      restoreButton.hidden = true;
      discardButton.hidden = true;
      setStatus("Autosave cleared");
    });

    window.addEventListener("beforeunload", (event) => {
      if (!dirty) {
        return;
      }
      event.preventDefault();
      event.returnValue = "";
    });

    return {
      markSaved,
      markDirty,
      isDirty: () => dirty,
    };
  };

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

      await adminJsonRequest(form.action, { method: "POST" }).catch(() => null);
      window.location.assign("/admin/login");
    });
  });

  document.querySelectorAll("[data-admin-article-editor]").forEach((form) => {
    const tagEditor = setupAdminTagEditor(form);
    setupAdminCategorySelector(form);
    setupAdminMarkdownEditor(form);
    const validationSummary = setupAdminValidationSummary(form);
    const autosave = setupArticleAutosave(form);

    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      const message = form.querySelector("[data-admin-form-message]");
      const submitButton = form.querySelector("[type='submit']");
      tagEditor.sync();
      validationSummary.clear();

      const validationMessages = collectArticleValidationMessages(form);
      if (validationMessages.length) {
        validationSummary.show(validationMessages);
        form.reportValidity();
        setAdminMessage(message, "Resolve the highlighted editor issues.", "error");
        return;
      }

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
        tags: splitAdminTags(formData.get("tags")),
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
        autosave.markSaved();
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
        await adminJsonRequest(deleteUrl, { method: "DELETE" });
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

  document.querySelectorAll("[data-admin-user-create-form]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      const message = form.querySelector("[data-admin-form-message]");
      const submitButton = form.querySelector("[type='submit']");
      if (!form.checkValidity()) {
        form.reportValidity();
        setAdminMessage(message, "Complete the admin account fields.", "error");
        return;
      }

      const formData = new FormData(form);
      const payload = {
        username: String(formData.get("username") || "").trim(),
        password: String(formData.get("password") || ""),
        role: String(formData.get("role") || "editor"),
      };

      if (submitButton) {
        submitButton.disabled = true;
      }
      setAdminMessage(message, "Creating admin user...");

      try {
        await adminJsonRequest(form.action, { method: "POST", body: payload });
        setAdminMessage(message, "Admin user created.", "success");
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

  document.querySelectorAll("[data-admin-user-role-form]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      const adminId = form.getAttribute("data-admin-user-id");
      const select = form.querySelector("select[name='role']");
      const message = document.querySelector("[data-admin-users-message]");
      const submitButton = form.querySelector("[type='submit']");
      if (!adminId || !select) {
        return;
      }

      if (submitButton) {
        submitButton.disabled = true;
      }

      try {
        const adminUser = await adminJsonRequest(`/api/admin/users/${adminId}/role`, {
          method: "PATCH",
          body: { role: select.value },
        });
        const updated = form
          .closest("[data-admin-user-row]")
          ?.querySelector("[data-admin-user-updated]");
        if (updated) {
          updated.textContent = formatAdminDate(adminUser.updated_at);
        }
        setAdminMessage(message, "Role updated.", "success");
      } catch (error) {
        setAdminMessage(message, error.message, "error");
      } finally {
        if (submitButton) {
          submitButton.disabled = false;
        }
      }
    });
  });

  document.querySelectorAll("[data-admin-user-password-form]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      const adminId = form.getAttribute("data-admin-user-id");
      const passwordInput = form.querySelector("input[name='password']");
      const message = document.querySelector("[data-admin-users-message]");
      const submitButton = form.querySelector("[type='submit']");
      if (!adminId || !passwordInput) {
        return;
      }

      if (!form.checkValidity()) {
        form.reportValidity();
        setAdminMessage(message, "Enter a password with at least 8 characters.", "error");
        return;
      }

      if (submitButton) {
        submitButton.disabled = true;
      }

      try {
        await adminJsonRequest(`/api/admin/users/${adminId}/password`, {
          method: "PATCH",
          body: { password: passwordInput.value },
        });
        form.reset();
        setAdminMessage(message, "Password updated.", "success");
      } catch (error) {
        setAdminMessage(message, error.message, "error");
      } finally {
        if (submitButton) {
          submitButton.disabled = false;
        }
      }
    });
  });

  document.querySelectorAll("[data-admin-user-status-toggle]").forEach((button) => {
    button.addEventListener("click", async () => {
      const adminId = button.getAttribute("data-admin-user-id");
      const isActive = button.getAttribute("data-is-active") === "true";
      const nextActive = !isActive;
      const message = document.querySelector("[data-admin-users-message]");
      if (!adminId) {
        return;
      }

      if (!nextActive && !window.confirm("Disable this admin account?")) {
        return;
      }

      button.disabled = true;
      try {
        const adminUser = await adminJsonRequest(`/api/admin/users/${adminId}/status`, {
          method: "PATCH",
          body: { is_active: nextActive },
        });
        const row = button.closest("[data-admin-user-row]");
        const status = row?.querySelector("[data-admin-user-status]");
        const updated = row?.querySelector("[data-admin-user-updated]");

        button.dataset.isActive = adminUser.is_active ? "true" : "false";
        button.textContent = adminUser.is_active ? "Disable" : "Reactivate";
        if (status) {
          status.textContent = adminUser.is_active ? "Active" : "Disabled";
        }
        if (updated) {
          updated.textContent = formatAdminDate(adminUser.updated_at);
        }
        setAdminMessage(message, "Account status updated.", "success");
      } catch (error) {
        setAdminMessage(message, error.message, "error");
      } finally {
        button.disabled = false;
      }
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
