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
