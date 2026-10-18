const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

document.addEventListener("DOMContentLoaded", () => {
  // Light or dark: switches night.css on or off and remembers the choice in a
  // cookie, so the server renders the next page in the same mode.
  const nightStyles = document.querySelector("[data-night-styles]");
  document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
    const isDark = () => window.matchMedia(nightStyles.media).matches;
    const label = () => button.setAttribute("aria-label", isDark() ? "Switch to light mode" : "Switch to dark mode");
    label();
    button.addEventListener("click", () => {
      const theme = isDark() ? "light" : "dark";
      nightStyles.media = theme === "dark" ? "all" : "not all";
      const secure = location.protocol === "https:" ? "; Secure" : "";
      document.cookie = `theme=${theme}; Path=/; Max-Age=31536000; SameSite=Lax${secure}`;
      label();
    });
  });

  if (window.bootstrap?.Tooltip) {
    document.querySelectorAll("[data-bs-toggle='tooltip']").forEach((element) => {
      new bootstrap.Tooltip(element);
    });
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
        message.textContent = "Enter a valid email to subscribe.";
        message.classList.add("is-error");
        return;
      }

      const email = emailInput?.value?.trim();
      if (!email) {
        message.textContent = "Enter a valid email to subscribe.";
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
          message.textContent = "You're on the list. Watch for the next email.";
          message.classList.add("is-success");
          form.reset();
          return;
        }

        message.textContent =
          payload?.error?.message ||
          (typeof payload?.detail === "string" ? payload.detail : "") ||
          "We could not save that email right now.";
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

  // One source per line, "Title | URL" or a bare URL. The server checks URLs.
  const parseAdminSources = (value) =>
    String(value || "")
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const divider = line.lastIndexOf("|");
        if (divider === -1) {
          return { title: line, url: line };
        }
        const url = line.slice(divider + 1).trim();
        return { title: line.slice(0, divider).trim() || url, url };
      });

  const escapeHtml = (value) =>
    String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");

  // Mirrors app/utils/markdown.py so the preview matches the published page.
  const formatInlineMarkdown = (html) =>
    html
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/_([^_]+)_/g, "<em>$1</em>");

  const renderInlineMarkdown = (value) => {
    // Links first, URLs untouched, so an underscore in a URL never breaks it.
    const html = escapeHtml(value);
    const linkPattern = /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g;
    const parts = [];
    let position = 0;
    for (const match of html.matchAll(linkPattern)) {
      parts.push(formatInlineMarkdown(html.slice(position, match.index)));
      parts.push(
        `<a href="${match[2]}" target="_blank" rel="noopener noreferrer nofollow">${formatInlineMarkdown(match[1])}</a>`,
      );
      position = match.index + match[0].length;
    }
    parts.push(formatInlineMarkdown(html.slice(position)));
    return parts.join("");
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

  // Member editor: same toolbar and preview, but the form posts normally.
  document.querySelectorAll("[data-markdown-editor]").forEach(setupAdminMarkdownEditor);

  // Member cover: preview the chosen file, the pasted link, the current cover,
  // or the drawn cover for the chosen room. The file is sent with the form.
  document.querySelectorAll("[data-cover-picker]").forEach((picker) => {
    const preview = picker.querySelector("[data-cover-preview]");
    const caption = picker.querySelector("[data-cover-caption]");
    const fileInput = picker.querySelector("[data-cover-file]");
    const linkInput = picker.querySelector("[data-cover-link]");
    const removeInput = picker.querySelector("[data-cover-remove]");
    const roomSelect = picker.form?.querySelector("[name='category_id']");
    const roomCovers = JSON.parse(picker.dataset.roomCovers || "{}");

    const drawnCover = () => roomCovers[roomSelect?.value] || Object.values(roomCovers)[0] || "";
    const show = (src, text) => {
      preview.src = src;
      caption.textContent = text;
    };
    const update = () => {
      const file = fileInput.files[0];
      const link = linkInput.value.trim();
      const ownCover = removeInput?.checked ? "" : preview.dataset.ownCover;
      if (file) {
        // A data: URL, because the page's security policy does not allow blob: images.
        const reader = new FileReader();
        reader.addEventListener("load", () => show(reader.result, "Your new image. It's saved when you save the piece."));
        reader.readAsDataURL(file);
      } else if (link.startsWith("https://")) {
        show(link, "The image from your link.");
      } else if (ownCover && !link && !ownCover.startsWith("https://")) {
        show(ownCover, "Your cover.");
      } else {
        show(drawnCover(), "Without an image, your piece gets a cover drawn for its room, like this one.");
      }
    };

    [fileInput, removeInput, roomSelect].forEach((input) => input?.addEventListener("change", update));
    linkInput.addEventListener("input", update);
  });

  document.querySelectorAll("[data-admin-article-editor]").forEach((form) => {
    // Cover upload: stores the image right away and puts its address in the
    // cover field; saving the article is what uses it.
    form.querySelectorAll("[data-admin-cover-file]").forEach((fileInput) => {
      const coverInput = form.querySelector("[name='cover_image']");
      const message = form.querySelector("[data-admin-cover-message]");
      fileInput.addEventListener("change", async () => {
        if (!fileInput.files[0]) {
          return;
        }
        const body = new FormData();
        body.append("file", fileInput.files[0]);
        setAdminMessage(message, "Uploading...");
        try {
          const response = await fetch("/api/admin/covers", {
            method: "POST",
            headers: { Accept: "application/json", "X-CSRF-Token": getAdminCsrfToken() },
            body,
          });
          const payload = await response.json().catch(() => ({}));
          if (!response.ok) {
            throw new Error(payload?.error?.message || payload?.detail || "Upload failed.");
          }
          coverInput.value = payload.url;
          setAdminMessage(message, "Uploaded. Save the article to use it.", "success");
        } catch (error) {
          setAdminMessage(message, error.message, "error");
        } finally {
          fileInput.value = "";
        }
      });
    });

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
        article_format: String(formData.get("article_format") || "article"),
        is_editors_pick: formData.get("is_editors_pick") === "true",
        is_speculative: formData.get("is_speculative") === "true",
        sources: parseAdminSources(formData.get("sources")),
        status,
        seo_title: String(formData.get("seo_title") || "").trim() || null,
        seo_description:
          String(formData.get("seo_description") || "").trim() || null,
      };

      if (formData.has("correction_note")) {
        payload.correction_note = String(formData.get("correction_note") || "").trim() || null;
      }
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

  document.querySelectorAll("[data-admin-send-back]").forEach((button) => {
    button.addEventListener("click", async () => {
      const form = button.closest("form");
      const message = form?.querySelector("[data-admin-form-message]");
      const note = form?.querySelector("[data-admin-send-back-note]")?.value.trim() || "";
      if (note.length < 3) {
        setAdminMessage(message, "Write a short note so the member knows what to change.", "error");
        return;
      }

      button.disabled = true;
      try {
        await adminJsonRequest(`/api/admin/articles/${button.getAttribute("data-article-id")}/send-back`, {
          method: "PATCH",
          body: { note },
        });
        setAdminMessage(message, "Sent back to the member.", "success");
        window.setTimeout(() => window.location.assign("/admin/articles#reviewQueue"), 450);
      } catch (error) {
        setAdminMessage(message, error.message, "error");
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
        const afterDelete = button.getAttribute("data-after-delete");
        if (afterDelete) {
          window.location.assign(afterDelete);
          return;
        }
        button.closest("tr, [data-admin-category-row]")?.remove();
        setAdminMessage(message, "Deleted.", "success");
      } catch (error) {
        setAdminMessage(message, error.message, "error");
      } finally {
        button.disabled = false;
      }
    });
  });

  document.querySelectorAll("[data-admin-question-form]").forEach((form) => {
    const message = form.querySelector("[data-admin-form-message]");
    const questionId = form.getAttribute("data-question-id");

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!form.checkValidity()) {
        form.reportValidity();
        return;
      }

      const formData = new FormData(form);
      const submitButton = form.querySelector("[type='submit']");
      submitButton.disabled = true;
      setAdminMessage(message, "Saving question...");
      try {
        const question = await adminJsonRequest(
          questionId ? `/api/admin/questions/${questionId}` : "/api/admin/questions",
          {
            method: questionId ? "PATCH" : "POST",
            body: {
              text: String(formData.get("text") || "").trim(),
              intro: String(formData.get("intro") || "").trim() || null,
              category_id: String(formData.get("category_id") || "") || null,
              publish_date: String(formData.get("publish_date") || ""),
              status: String(formData.get("status") || "draft"),
            },
          },
        );
        setAdminMessage(message, "Question saved.", "success");
        window.setTimeout(() => window.location.assign(`/admin/questions/${question.id}`), 450);
      } catch (error) {
        setAdminMessage(message, error.message, "error");
        submitButton.disabled = false;
      }
    });
  });

  document.querySelectorAll("[data-admin-quiz-form]").forEach((form) => {
    const message = form.querySelector("[data-admin-form-message]");
    const itemId = form.getAttribute("data-item-id");

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!form.checkValidity()) {
        form.reportValidity();
        return;
      }

      const formData = new FormData(form);
      const submitButton = form.querySelector("[type='submit']");
      submitButton.disabled = true;
      setAdminMessage(message, "Saving claim...");
      try {
        const item = await adminJsonRequest(
          itemId ? `/api/admin/quiz-items/${itemId}` : "/api/admin/quiz-items",
          {
            method: itemId ? "PATCH" : "POST",
            body: {
              claim: String(formData.get("claim") || "").trim(),
              is_true: formData.get("is_true") === "true",
              explanation: String(formData.get("explanation") || "").trim(),
              article_slug: String(formData.get("article_slug") || "") || null,
              category_id: String(formData.get("category_id") || "") || null,
              status: String(formData.get("status") || "draft"),
            },
          },
        );
        setAdminMessage(message, "Claim saved.", "success");
        window.setTimeout(() => window.location.assign(`/admin/arcade/${item.id}`), 450);
      } catch (error) {
        setAdminMessage(message, error.message, "error");
        submitButton.disabled = false;
      }
    });
  });

  document.querySelectorAll("[data-admin-response-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      const message = document.querySelector("[data-admin-table-message]");
      const field = button.getAttribute("data-field");
      const raw = button.getAttribute("data-value");
      button.disabled = true;
      try {
        await adminJsonRequest(`/api/admin/responses/${button.getAttribute("data-response-id")}`, {
          method: "PATCH",
          body: { [field]: field === "is_featured" ? raw === "true" : raw },
        });
        window.location.reload();
      } catch (error) {
        setAdminMessage(message, error.message, "error");
        button.disabled = false;
      }
    });
  });

  // Account deletions: every deletion goes through a preview, then a confirm.
  document.querySelectorAll("[data-admin-deletions]").forEach((root) => {
    const message = root.querySelector("[data-admin-table-message]");
    const emailsInput = root.querySelector("[data-deletion-emails]");
    const review = root.querySelector("[data-deletion-review]");
    const reviewRows = root.querySelector("[data-deletion-review-rows]");
    const reviewTitle = root.querySelector("[data-deletion-review-title]");
    const confirm = root.querySelector("[data-deletion-confirm]");
    let pendingEmails = "";

    const row = (item) => {
      const article = document.createElement("article");
      article.className = "admin-resource-row";
      const body = document.createElement("div");
      const name = document.createElement("strong");
      const detail = document.createElement("small");
      if (item.found) {
        name.textContent = `${item.display_name} (@${item.username})`;
        detail.textContent = `${item.email}${item.requested ? " · asked to be deleted" : " · did not ask"} · ` +
          `${item.pieces} pieces, ${item.responses} responses, ${item.comments} comments, ${item.saved} saved`;
      } else {
        name.textContent = item.email;
        detail.textContent = "No account with this address; nothing to delete.";
      }
      body.append(name, detail);
      article.append(body);
      return article;
    };

    const preview = async (emails) => {
      if (!emails.trim()) {
        setAdminMessage(message, "Enter or select at least one email address.", "error");
        return;
      }
      try {
        const { rows } = await adminJsonRequest("/api/admin/deletions/preview", { method: "POST", body: { emails } });
        const found = rows.filter((item) => item.found);
        reviewRows.replaceChildren(...rows.map(row));
        reviewTitle.textContent = `${found.length} account${found.length === 1 ? "" : "s"} will be deleted`;
        confirm.hidden = found.length === 0;
        confirm.textContent = `Delete ${found.length} account${found.length === 1 ? "" : "s"} and everything they wrote`;
        pendingEmails = found.map((item) => item.email).join("\n");
        review.hidden = false;
        review.scrollIntoView({ behavior: prefersReducedMotion ? "auto" : "smooth", block: "start" });
        setAdminMessage(message, "Check the list, then confirm.");
      } catch (error) {
        setAdminMessage(message, error.message, "error");
      }
    };

    root.querySelector("[data-deletion-preview]")?.addEventListener("click", () => preview(emailsInput.value));
    root.querySelector("[data-deletion-preview-selected]")?.addEventListener("click", () => {
      const picked = [...root.querySelectorAll("[data-deletion-pick]:checked")].map((box) => box.value);
      preview(picked.join("\n"));
    });
    root.querySelector("[data-deletion-back]")?.addEventListener("click", () => {
      review.hidden = true;
      pendingEmails = "";
    });
    confirm?.addEventListener("click", async () => {
      confirm.disabled = true;
      try {
        const { results } = await adminJsonRequest("/api/admin/deletions/delete", { method: "POST", body: { emails: pendingEmails } });
        const deleted = results.filter((item) => item.deleted).length;
        setAdminMessage(message, `Deleted ${deleted} account${deleted === 1 ? "" : "s"}.`, "success");
        window.setTimeout(() => window.location.reload(), 1200);
      } catch (error) {
        setAdminMessage(message, error.message, "error");
        confirm.disabled = false;
      }
    });
    root.querySelectorAll("[data-deletion-cancel]").forEach((button) => {
      button.addEventListener("click", async () => {
        button.disabled = true;
        try {
          await adminJsonRequest(`/api/admin/deletions/${button.getAttribute("data-deletion-cancel")}/cancel`, { method: "POST" });
          window.location.reload();
        } catch (error) {
          setAdminMessage(message, error.message, "error");
          button.disabled = false;
        }
      });
    });
  });

  document.querySelectorAll("[data-admin-report-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      const message = document.querySelector("[data-admin-table-message]");
      button.disabled = true;
      try {
        await adminJsonRequest("/api/admin/reports/action", {
          method: "POST",
          body: {
            target_type: button.getAttribute("data-target-type"),
            target_id: button.getAttribute("data-target-id"),
            action: button.getAttribute("data-action"),
          },
        });
        window.location.reload();
      } catch (error) {
        setAdminMessage(message, error.message, "error");
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
        subtitle: String(formData.get("subtitle") || "").trim() || null,
        description: String(formData.get("description") || "").trim() || null,
        image: String(formData.get("image") || "").trim() || null,
        nav_order: Number(formData.get("nav_order") || 0),
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
      form.querySelector("input[name='subtitle']").value =
        row.getAttribute("data-category-subtitle") || "";
      form.querySelector("textarea[name='description']").value =
        row.getAttribute("data-category-description") || "";
      form.querySelector("input[name='image']").value =
        row.getAttribute("data-category-image") || "";
      form.querySelector("input[name='nav_order']").value =
        row.getAttribute("data-category-nav-order") || "0";
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
