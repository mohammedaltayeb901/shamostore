(() => {
  const toggle = document.querySelector("[data-nav-toggle]");
  const links = document.querySelector("[data-nav-links]");
  if (toggle && links) {
    toggle.addEventListener("click", () => {
      const open = links.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", String(open));
    });
  }

  document.querySelectorAll("[data-amount-chip]").forEach((chip) => {
    chip.addEventListener("click", () => {
      const input = document.querySelector("#amount");
      if (input) {
        input.value = chip.dataset.amountChip;
        input.focus();
      }
    });
  });

  document.querySelectorAll("[data-confirm]").forEach((el) => {
    el.addEventListener("submit", (event) => {
      if (!window.confirm(el.dataset.confirm)) event.preventDefault();
    });
  });

  document.addEventListener("click", (event) => {
    document.querySelectorAll("details.user-menu[open]").forEach((menu) => {
      if (!menu.contains(event.target)) menu.removeAttribute("open");
    });
  });
})();
