document.querySelectorAll("[data-sector-selector]").forEach((selector) => {
  const options = selector.querySelectorAll(
    '.sector-form__candidate input[name="jefes_servicio"]'
  );
  const selectedList = selector.querySelector("[data-selected-list]");
  const selectedCount = selector.querySelector("[data-selection-count]");
  const emptyMessage = selector.querySelector("[data-empty-selection]");

  const renderSelected = () => {
    selectedList.querySelectorAll(".sector-form__selected-item").forEach((item) => item.remove());
    const selectedOptions = [...options].filter((option) => option.checked);

    selectedOptions.forEach((option) => {
      const item = document.createElement("div");
      item.className = "sector-form__selected-item";
      item.setAttribute("role", "listitem");
      item.textContent = option.closest("label").querySelector("span").textContent.trim();
      selectedList.append(item);
    });

    selectedCount.textContent = selectedOptions.length;
    emptyMessage.hidden = selectedOptions.length > 0;
  };

  options.forEach((option) => option.addEventListener("change", renderSelected));
  renderSelected();
});