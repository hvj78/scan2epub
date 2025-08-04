(function () {
  // Language detection: default HU if browser language starts with 'hu', else EN.
  const saved = localStorage.getItem("s2e-lang");
  const browserLang = (navigator.language || navigator.userLanguage || "en").toLowerCase();
  const prefersHu = browserLang.startsWith("hu");
  const initial = saved || (prefersHu ? "hu" : "en");
  setLang(initial);

  // Wire language toggle button
  const toggleBtn = document.getElementById("langToggle");
  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      const current = document.documentElement.lang === "hu" ? "en" : "hu";
      setLang(current);
    });
  }

  // Copy command button
  const copyBtn = document.getElementById("copyBtn");
  if (copyBtn) {
    copyBtn.addEventListener("click", async () => {
      const code = document.getElementById("cmd");
      if (!code) return;
      const text = code.innerText.trim();
      try {
        await navigator.clipboard.writeText(text);
        flash(copyBtn);
      } catch {
        // Fallback for older browsers
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.left = "-9999px";
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        ta.remove();
        flash(copyBtn);
      }
    });
  }

  // Year in footer
  const yearEl = document.getElementById("year");
  if (yearEl) yearEl.textContent = new Date().getFullYear().toString();

  function setLang(lang) {
    document.documentElement.setAttribute("lang", lang);
    const toggleBtn = document.getElementById("langToggle");
    if (toggleBtn) toggleBtn.textContent = lang === "hu" ? "HU" : "EN";
    localStorage.setItem("s2e-lang", lang);
    // Update nav labels (progressive enhancement if JS-only labels are desired in future)
  }

  function flash(btn) {
    const original = btn.textContent;
    const isHu = document.documentElement.lang === "hu";
    btn.textContent = isHu ? "Másolva!" : "Copied!";
    btn.disabled = true;
    setTimeout(() => {
      btn.textContent = original;
      btn.disabled = false;
    }, 1200);
  }
})();
