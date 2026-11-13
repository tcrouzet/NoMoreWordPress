document.addEventListener("DOMContentLoaded", () => {
  const frames = document.querySelectorAll(".prose iframe");

  frames.forEach((frame, index) => {
    const shell = document.createElement("div");
    const button = document.createElement("button");
    const isVisuGpx = frame.src.includes("visugpx.com");

    shell.className = "iframe-shell";
    frame.parentNode.insertBefore(shell, frame);
    shell.appendChild(frame);

    const alignToViewport = () => {
      const viewportWidth = window.innerWidth;
      shell.style.setProperty("width", `${viewportWidth}px`, "important");
      shell.style.setProperty("max-width", `${viewportWidth}px`, "important");
      shell.style.setProperty("margin-left", "0", "important");
      shell.style.setProperty("margin-right", "0", "important");
      shell.style.setProperty("transform", "none");
      const shellLeft = shell.getBoundingClientRect().left;
      shell.style.setProperty("transform", `translateX(${-shellLeft}px)`);
      if (isVisuGpx) {
        frame.style.setProperty("width", `${viewportWidth + 6}px`, "important");
        frame.style.setProperty("max-width", "none", "important");
        frame.style.setProperty("transform", "translateX(-3px)");
        frame.style.setProperty("resize", "none", "important");
      } else {
        frame.style.setProperty("width", "100%", "important");
        frame.style.setProperty("max-width", "100%", "important");
      }
    };

    requestAnimationFrame(alignToViewport);
    window.addEventListener("resize", alignToViewport);
    window.visualViewport?.addEventListener("resize", alignToViewport);

    frame.classList.add("iframe-locked");
    frame.setAttribute("tabindex", "-1");

    button.type = "button";
    button.className = "iframe-activation";
    button.setAttribute("aria-label", "Activer le contenu interactif");
    button.setAttribute("aria-pressed", "false");
    button.setAttribute("aria-controls", `interactive-frame-${index + 1}`);

    if (!frame.id) {
      frame.id = `interactive-frame-${index + 1}`;
    } else {
      button.setAttribute("aria-controls", frame.id);
    }

    shell.appendChild(button);

    const deactivate = () => {
      shell.classList.remove("is-active");
      frame.classList.add("iframe-locked");
      frame.setAttribute("tabindex", "-1");
      button.setAttribute("aria-pressed", "false");
    };

    const activate = () => {
      document.querySelectorAll(".iframe-shell.is-active").forEach(activeShell => {
        if (activeShell !== shell) {
          activeShell.querySelector(".iframe-activation")?.click();
        }
      });
      shell.classList.add("is-active");
      frame.classList.remove("iframe-locked");
      frame.setAttribute("tabindex", "0");
      button.setAttribute("aria-pressed", "true");
      frame.focus({ preventScroll: true });
    };

    button.addEventListener("click", () => {
      if (shell.classList.contains("is-active")) {
        deactivate();
      } else {
        activate();
      }
    });

    shell.addEventListener("keydown", event => {
      if (event.key === "Escape" && shell.classList.contains("is-active")) {
        deactivate();
        button.focus();
      }
    });

    shell.addEventListener("pointerleave", event => {
      if (event.pointerType === "mouse" && shell.classList.contains("is-active")) {
        deactivate();
      }
    });

    document.addEventListener("pointerdown", event => {
      if (shell.classList.contains("is-active") && !shell.contains(event.target)) {
        deactivate();
      }
    });
  });

  const shareButton = document.querySelector(".footer-share");
  if (shareButton) {
    const copyUrl = async () => {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(window.location.href);
      } else {
        const field = document.createElement("textarea");
        field.value = window.location.href;
        field.style.position = "fixed";
        field.style.opacity = "0";
        document.body.appendChild(field);
        field.select();
        document.execCommand("copy");
        field.remove();
      }
      const initialLabel = shareButton.textContent;
      shareButton.textContent = "Lien copié";
      window.setTimeout(() => { shareButton.textContent = initialLabel; }, 1800);
    };

    shareButton.addEventListener("click", async () => {
      try {
        if (navigator.share) {
          await navigator.share({
            title: document.title,
            url: window.location.href
          });
        } else {
          await copyUrl();
        }
      } catch (error) {
        if (error.name !== "AbortError") {
          await copyUrl();
        }
      }
    });
  }

  document.querySelectorAll("[data-countdown]").forEach(countdown => {
    const rawDate = countdown.dataset.countdown.trim()
      .replace(/^[‘’'"\s]+|[‘’'"\s]+$/g, "");
    const target = new Date(rawDate);
    const output = countdown.querySelector("span");

    if (Number.isNaN(target.getTime())) {
      countdown.hidden = true;
      return;
    }

    let timer;
    const updateCountdown = () => {
      const difference = target.getTime() - Date.now();
      if (difference <= 0) {
        output.textContent = "Événement terminé";
        if (timer) window.clearInterval(timer);
        return;
      }

      const days = Math.floor(difference / 86400000);
      const hours = Math.floor(difference / 3600000) % 24;
      const minutes = Math.floor(difference / 60000) % 60;
      const seconds = String(Math.floor(difference / 1000) % 60).padStart(2, "0");
      output.textContent = `${days} jours ${hours}h${minutes}:${seconds}`;
    };

    updateCountdown();
    if (target.getTime() > Date.now()) {
      timer = window.setInterval(updateCountdown, 1000);
    }
  });
});
