const apiBase = "http://127.0.0.1:8000";

const storageRootInput = document.getElementById("storageRoot");
const saveRootButton = document.getElementById("saveRoot");
const statusEl = document.getElementById("rootStatus");
const healthButton = document.getElementById("healthCheck");
const healthResult = document.getElementById("healthResult");
const agentProviderSelect = document.getElementById("agentProvider");
const agentEndpointInput = document.getElementById("agentEndpoint");
const agentModelInput = document.getElementById("agentModel");
const agentApiKeyInput = document.getElementById("agentApiKey");
const agentTimeoutInput = document.getElementById("agentTimeout");
const saveAgentConfigButton = document.getElementById("saveAgentConfig");
const agentConfigStatus = document.getElementById("agentConfigStatus");

const uploadForm = document.getElementById("uploadForm");
const titleInput = document.getElementById("titleInput");
const authorsInput = document.getElementById("authorsInput");
const yearInput = document.getElementById("yearInput");
const journalInput = document.getElementById("journalInput");
const abstractInput = document.getElementById("abstractInput");
const citationInput = document.getElementById("citationInput");
const categorySelect = document.getElementById("categorySelect");
const subdirInput = document.getElementById("subdirInput");
const fileInput = document.getElementById("fileInput");
const uploadStatus = document.getElementById("uploadStatus");
const literatureList = document.getElementById("literatureList");
const refreshListButton = document.getElementById("refreshList");
const searchInput = document.getElementById("searchInput");
const searchCategory = document.getElementById("searchCategory");
const yearStartInput = document.getElementById("yearStart");
const yearEndInput = document.getElementById("yearEnd");
const runSearchButton = document.getElementById("runSearch");
const sortBySelect = document.getElementById("sortBy");
const sortOrderSelect = document.getElementById("sortOrder");
const pageSizeSelect = document.getElementById("pageSize");
const prevPageButton = document.getElementById("prevPage");
const nextPageButton = document.getElementById("nextPage");
const pageInfo = document.getElementById("pageInfo");
const newCategoryInput = document.getElementById("newCategoryInput");
const addCategoryButton = document.getElementById("addCategory");
const categoryStatus = document.getElementById("categoryStatus");
const categoryList = document.getElementById("categoryList");
const uploadProgress = document.getElementById("uploadProgress");

const editModal = document.getElementById("editModal");
const closeEditButton = document.getElementById("closeEdit");
const editTitle = document.getElementById("editTitle");
const editAuthors = document.getElementById("editAuthors");
const editYear = document.getElementById("editYear");
const editJournal = document.getElementById("editJournal");
const editAbstract = document.getElementById("editAbstract");
const editCitation = document.getElementById("editCitation");
const editCategory = document.getElementById("editCategory");
const saveEditButton = document.getElementById("saveEdit");
const agentSuggestButton = document.getElementById("agentSuggest");
const agentStatus = document.getElementById("agentStatus");
const agentMeta = document.getElementById("agentMeta");
const toastContainer = document.getElementById("toastContainer");

const detailModal = document.getElementById("detailModal");
const closeDetailButton = document.getElementById("closeDetail");
const detailTitle = document.getElementById("detailTitle");
const detailAuthors = document.getElementById("detailAuthors");
const detailYear = document.getElementById("detailYear");
const detailJournal = document.getElementById("detailJournal");
const detailCategory = document.getElementById("detailCategory");
const detailAbstract = document.getElementById("detailAbstract");
const detailCitation = document.getElementById("detailCitation");
const detailFile = document.getElementById("detailFile");

let categoryMap = new Map();
let literatureCache = new Map();
let activeLiteratureId = null;
let currentPage = 1;
let pageSize = 25;
let currentMode = "list";

function showToast(type, title, message) {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <div class="title">${title}</div>
    <div class="message">${message}</div>
  `;
  toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 3500);
}

function isYearValid(yearValue) {
  if (!yearValue) {
    return true;
  }
  const year = Number(yearValue);
  return Number.isFinite(year) && year >= 1800 && year <= 2100;
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  let payload = {};
  try {
    payload = await response.json();
  } catch (error) {
    payload = {};
  }
  if (!response.ok) {
    const message = payload.detail || "Request failed";
    throw new Error(message);
  }
  return payload;
}

async function loadStorageRoot() {
  const data = await fetchJson(`${apiBase}/config/storage-root`);
  storageRootInput.value = data.storage_root || "";
}

async function saveStorageRoot() {
  const payload = { storage_root: storageRootInput.value };
  const data = await fetchJson(`${apiBase}/config/storage-root`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  statusEl.textContent = `Saved: ${data.storage_root}`;
  showToast("success", "Storage root", "Path updated successfully.");
}

async function pingApi() {
  const data = await fetchJson(`${apiBase}/`);
  healthResult.textContent = JSON.stringify(data, null, 2);
  showToast("success", "API", "Backend is responding.");
}

async function loadAgentConfig() {
  if (!agentProviderSelect) {
    return;
  }
  const data = await fetchJson(`${apiBase}/config/agent`);
  agentProviderSelect.value = data.ai_provider || "disabled";
  agentEndpointInput.value = data.ai_custom_endpoint || "";
  agentModelInput.value = data.ai_model || "";
  agentApiKeyInput.value = "";
  agentTimeoutInput.value = data.ai_timeout_seconds || 30;
}

async function saveAgentConfig() {
  if (!agentProviderSelect) {
    return;
  }
  const payload = {
    ai_provider: agentProviderSelect.value || "disabled",
    ai_custom_endpoint: agentEndpointInput.value.trim() || "",
    ai_api_key: agentApiKeyInput.value || "",
    ai_model: agentModelInput.value.trim() || "",
    ai_timeout_seconds: agentTimeoutInput.value
      ? Number(agentTimeoutInput.value)
      : 30,
  };
  const data = await fetchJson(`${apiBase}/config/agent`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  agentConfigStatus.textContent = "Agent config saved.";
  agentApiKeyInput.value = "";
  updateAgentMeta(await fetchAgentStatus());
  return data;
}

async function loadCategories() {
  const data = await fetchJson(`${apiBase}/categories`);
  categoryMap = new Map(data.map((item) => [item.id, item.name]));
  categorySelect.innerHTML = '<option value="">No category</option>';
  searchCategory.innerHTML = '<option value="">All categories</option>';
  editCategory.innerHTML = '<option value="">No category</option>';
  categoryList.innerHTML = "";
  data.forEach((category) => {
    const option = document.createElement("option");
    option.value = category.id;
    option.textContent = category.name;
    categorySelect.appendChild(option);
    const searchOption = document.createElement("option");
    searchOption.value = category.id;
    searchOption.textContent = category.name;
    searchCategory.appendChild(searchOption);
    const editOption = document.createElement("option");
    editOption.value = category.id;
    editOption.textContent = category.name;
    editCategory.appendChild(editOption);

    const pill = document.createElement("div");
    pill.className = "pill";
    pill.innerHTML = `
      <span>${category.name}</span>
      <button class="ghost" data-action="rename" data-id="${category.id}">Rename</button>
      <button data-action="delete" data-id="${category.id}">Delete</button>
    `;
    categoryList.appendChild(pill);
  });
}

function renderLiteratures(items) {
  literatureList.innerHTML = "";
  literatureCache = new Map(items.map((item) => [item.id, item]));
  if (!items.length) {
    literatureList.innerHTML =
      '<div class="table-empty">No literature yet. Upload a file to start.</div>';
    return;
  }

  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "table-row";
    row.innerHTML = `
      <span>${item.title || "Untitled"}</span>
      <span>${item.authors || "-"}</span>
      <span>${item.year || "-"}</span>
      <span>${categoryMap.get(item.category_id) || "-"}</span>
      <div class="actions">
        <button class="ghost" data-action="view" data-id="${item.id}">View</button>
        <button class="ghost" data-action="edit" data-id="${item.id}">Edit</button>
        <button data-action="delete" data-id="${item.id}">Delete</button>
      </div>
    `;
    literatureList.appendChild(row);
  });
}

async function loadLiteratures() {
  const params = new URLSearchParams();
  params.set("limit", String(pageSize));
  params.set("offset", String((currentPage - 1) * pageSize));
  params.set("sort_by", sortBySelect.value);
  params.set("sort_order", sortOrderSelect.value);
  const data = await fetchJson(`${apiBase}/literatures?${params.toString()}`);
  renderLiteratures(data);
  pageInfo.textContent = `Page ${currentPage}`;
  prevPageButton.disabled = currentPage === 1;
  nextPageButton.disabled = data.length < pageSize;
}

async function updateLiterature(literatureId, payload) {
  await fetchJson(`${apiBase}/literatures/${literatureId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

async function createCategory(name) {
  return fetchJson(`${apiBase}/categories`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

async function renameCategory(categoryId, name) {
  return fetchJson(`${apiBase}/categories/${categoryId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

async function deleteCategory(categoryId) {
  return fetchJson(`${apiBase}/categories/${categoryId}`, {
    method: "DELETE",
  });
}

async function deleteLiterature(literatureId) {
  await fetchJson(`${apiBase}/literatures/${literatureId}`, {
    method: "DELETE",
  });
}

async function handleEdit(literatureId) {
  const item = literatureCache.get(literatureId);
  if (!item) {
    return;
  }
  activeLiteratureId = literatureId;
  editTitle.value = item.title || "";
  editAuthors.value = item.authors || "";
  editYear.value = item.year || "";
  editJournal.value = item.journal || "";
  editAbstract.value = item.abstract || "";
  editCitation.value = item.citation || "";
  editCategory.value = item.category_id || "";
  agentStatus.textContent = "";
  if (agentMeta) {
    agentMeta.textContent = "Agent: checking...";
    fetchAgentStatus().catch(() => {
      agentMeta.textContent = "Agent: unavailable";
    });
  }
  editModal.classList.remove("hidden");
}

async function handleView(literatureId) {
  const item = literatureCache.get(literatureId);
  if (!item) {
    return;
  }
  detailTitle.textContent = item.title || "";
  detailAuthors.textContent = item.authors || "";
  detailYear.textContent = item.year || "";
  detailJournal.textContent = item.journal || "";
  detailCategory.textContent = categoryMap.get(item.category_id) || "";
  detailAbstract.textContent = item.abstract || "";
  detailCitation.textContent = item.citation || "";
  detailFile.textContent = item.file_path || "";
  detailModal.classList.remove("hidden");
}

async function handleDelete(literatureId) {
  const ok = window.confirm("Delete this literature item?");
  if (!ok) {
    return;
  }
  await deleteLiterature(literatureId);
  await loadLiteratures();
  showToast("success", "Deleted", "Literature removed.");
}

async function fetchAgentStatus() {
  const data = await fetchJson(`${apiBase}/agent/status`);
  updateAgentMeta(data);
  return data;
}

function updateAgentMeta(status) {
  if (!agentMeta) {
    return;
  }
  if (!status) {
    agentMeta.textContent = "Agent: unknown";
    agentSuggestButton.disabled = true;
    return;
  }
  if (!status.available) {
    agentMeta.textContent = `Agent: offline (${status.mode})`;
    agentSuggestButton.disabled = true;
    return;
  }
  const model = status.model ? ` (${status.model})` : "";
  agentMeta.textContent = `Agent: ${status.mode}${model}`;
  agentSuggestButton.disabled = false;
}

async function runAgentSuggest() {
  if (!activeLiteratureId) {
    return;
  }
  const data = await fetchJson(`${apiBase}/agent/suggest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ literature_id: activeLiteratureId }),
  });

  if (data.title) editTitle.value = data.title;
  if (data.authors) editAuthors.value = data.authors;
  if (data.year) editYear.value = data.year;

  if (data.category_suggest) {
    const match = [...categoryMap.entries()].find(
      ([, name]) => name.toLowerCase() === data.category_suggest.toLowerCase(),
    );
    if (match) {
      editCategory.value = match[0];
    }
  }
  agentStatus.textContent = "Agent suggestions applied.";
  showToast("success", "Agent", "Suggestions applied.");
}

async function runSearch() {
  const params = new URLSearchParams();
  if (searchInput.value.trim()) params.set("q", searchInput.value.trim());
  if (searchCategory.value) params.set("category_id", searchCategory.value);
  if (yearStartInput.value) params.set("year_start", yearStartInput.value);
  if (yearEndInput.value) params.set("year_end", yearEndInput.value);

  params.set("limit", String(pageSize));
  params.set("offset", String((currentPage - 1) * pageSize));
  params.set("sort_by", sortBySelect.value);
  params.set("sort_order", sortOrderSelect.value);

  const query = params.toString();
  const url = `${apiBase}/search?${query}`;
  const data = await fetchJson(url);
  const items = Array.isArray(data.items)
    ? data.items.map((hit) => hit.literature)
    : [];
  renderLiteratures(items);
  pageInfo.textContent = `Page ${currentPage}`;
  prevPageButton.disabled = currentPage === 1;
  nextPageButton.disabled = items.length < pageSize;
}

async function handleUpload(event) {
  event.preventDefault();
  uploadStatus.textContent = "";
  uploadStatus.classList.remove("error");

  if (!isYearValid(yearInput.value)) {
    uploadStatus.textContent = "Year must be between 1800 and 2100.";
    uploadStatus.classList.add("error");
    showToast("error", "Upload", "Invalid year range.");
    return;
  }

  const file = fileInput.files[0];
  if (!file) {
    uploadStatus.textContent = "Please choose a file.";
    uploadStatus.classList.add("error");
    showToast("error", "Upload", "Please choose a file.");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  if (titleInput.value) formData.append("title", titleInput.value);
  if (authorsInput.value) formData.append("authors", authorsInput.value);
  if (yearInput.value) formData.append("year", yearInput.value);
  if (journalInput.value) formData.append("journal", journalInput.value);
  if (abstractInput.value) formData.append("abstract", abstractInput.value);
  if (citationInput.value) formData.append("citation", citationInput.value);
  if (categorySelect.value)
    formData.append("category_id", categorySelect.value);
  if (subdirInput.value) formData.append("subdir", subdirInput.value);

  uploadStatus.textContent = "Uploading...";
  uploadStatus.classList.remove("error");
  uploadProgress.style.width = "0%";

  await new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${apiBase}/literatures/upload`);
    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) {
        const percent = Math.round((event.loaded / event.total) * 100);
        uploadProgress.style.width = `${percent}%`;
      }
    });
    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve();
      } else {
        let message = "Upload failed";
        try {
          const response = JSON.parse(xhr.responseText);
          message = response.detail || response.error?.message || message;
        } catch (error) {
          message = "Upload failed";
        }
        reject(new Error(message));
      }
    });
    xhr.addEventListener("error", () => reject(new Error("Upload failed")));
    xhr.send(formData);
  });

  uploadStatus.textContent = "Upload complete.";
  uploadForm.reset();
  await loadLiteratures();
  uploadProgress.style.width = "0%";
  showToast("success", "Upload", "File uploaded successfully.");
}

saveRootButton.addEventListener("click", () => {
  saveStorageRoot().catch((error) => {
    statusEl.textContent = error.message;
    showToast("error", "Storage root", error.message);
  });
});

if (saveAgentConfigButton) {
  saveAgentConfigButton.addEventListener("click", () => {
    agentConfigStatus.textContent = "";
    saveAgentConfig().catch((error) => {
      agentConfigStatus.textContent = error.message;
      agentConfigStatus.classList.add("error");
      showToast("error", "Agent config", error.message);
    });
  });
}

healthButton.addEventListener("click", () => {
  pingApi().catch(() => {
    healthResult.textContent = "Ping failed";
    showToast("error", "API", "Ping failed.");
  });
});

uploadForm.addEventListener("submit", (event) => {
  handleUpload(event).catch((error) => {
    uploadStatus.textContent = error.message;
    uploadStatus.classList.add("error");
    showToast("error", "Upload", error.message);
  });
});

refreshListButton.addEventListener("click", () => {
  currentMode = "list";
  currentPage = 1;
  loadLiteratures().catch(() => {
    literatureList.innerHTML =
      '<div class="table-empty">Failed to load list.</div>';
  });
});

runSearchButton.addEventListener("click", () => {
  currentMode = "search";
  currentPage = 1;
  runSearch().catch(() => {
    literatureList.innerHTML = '<div class="table-empty">Search failed.</div>';
  });
});

sortBySelect.addEventListener("change", () => {
  currentPage = 1;
  if (currentMode === "search") {
    runSearch().catch(() => {});
  } else {
    loadLiteratures().catch(() => {});
  }
});

sortOrderSelect.addEventListener("change", () => {
  currentPage = 1;
  if (currentMode === "search") {
    runSearch().catch(() => {});
  } else {
    loadLiteratures().catch(() => {});
  }
});

pageSizeSelect.addEventListener("change", () => {
  pageSize = Number(pageSizeSelect.value);
  currentPage = 1;
  if (currentMode === "search") {
    runSearch().catch(() => {});
  } else {
    loadLiteratures().catch(() => {});
  }
});

prevPageButton.addEventListener("click", () => {
  if (currentPage === 1) {
    return;
  }
  currentPage -= 1;
  if (currentMode === "search") {
    runSearch().catch(() => {});
  } else {
    loadLiteratures().catch(() => {});
  }
});

nextPageButton.addEventListener("click", () => {
  currentPage += 1;
  if (currentMode === "search") {
    runSearch().catch(() => {});
  } else {
    loadLiteratures().catch(() => {});
  }
});

addCategoryButton.addEventListener("click", () => {
  const name = newCategoryInput.value.trim();
  if (!name) {
    categoryStatus.textContent = "Please enter a category name.";
    categoryStatus.classList.add("error");
    showToast("error", "Category", "Please enter a category name.");
    return;
  }
  createCategory(name)
    .then(() => {
      categoryStatus.textContent = "Category added.";
      categoryStatus.classList.remove("error");
      newCategoryInput.value = "";
      showToast("success", "Category", "Category added.");
      return loadCategories();
    })
    .catch((error) => {
      categoryStatus.textContent = error.message;
      categoryStatus.classList.add("error");
      showToast("error", "Category", error.message);
    });
});

categoryList.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) {
    return;
  }
  const action = target.dataset.action;
  const id = target.dataset.id;
  if (!action || !id) {
    return;
  }

  if (action === "rename") {
    const newName = window.prompt("New category name");
    if (!newName) {
      return;
    }
    renameCategory(Number(id), newName)
      .then(() => loadCategories())
      .catch((error) => {
        categoryStatus.textContent = error.message;
        categoryStatus.classList.add("error");
        showToast("error", "Category", error.message);
      });
  }

  if (action === "delete") {
    const hasItems = [...literatureCache.values()].some(
      (item) => item.category_id === Number(id),
    );
    if (hasItems) {
      showToast(
        "error",
        "Category",
        "This category has literatures. Move them first.",
      );
      return;
    }
    const ok = window.confirm("Delete this category?");
    if (!ok) {
      return;
    }
    deleteCategory(Number(id))
      .then(() => {
        showToast("success", "Category", "Category deleted.");
        return loadCategories();
      })
      .catch((error) => {
        categoryStatus.textContent = error.message;
        categoryStatus.classList.add("error");
        showToast("error", "Category", error.message);
      });
  }
});

saveEditButton.addEventListener("click", () => {
  if (!activeLiteratureId) {
    return;
  }
  if (!editTitle.value.trim()) {
    agentStatus.textContent = "Title is required.";
    agentStatus.classList.add("error");
    showToast("error", "Edit", "Title is required.");
    return;
  }
  if (!isYearValid(editYear.value)) {
    agentStatus.textContent = "Year must be between 1800 and 2100.";
    agentStatus.classList.add("error");
    showToast("error", "Edit", "Invalid year range.");
    return;
  }
  const payload = {
    title: editTitle.value.trim() || null,
    authors: editAuthors.value.trim() || null,
    year: editYear.value ? Number(editYear.value) : null,
    journal: editJournal.value.trim() || null,
    abstract: editAbstract.value.trim() || null,
    citation: editCitation.value.trim() || null,
    category_id: editCategory.value ? Number(editCategory.value) : null,
  };
  updateLiterature(activeLiteratureId, payload)
    .then(() => {
      editModal.classList.add("hidden");
      showToast("success", "Edit", "Literature updated.");
      return loadLiteratures();
    })
    .catch(() => {
      agentStatus.textContent = "Update failed.";
      agentStatus.classList.add("error");
      showToast("error", "Edit", "Update failed.");
    });
});

agentSuggestButton.addEventListener("click", () => {
  agentStatus.textContent = "Asking agent...";
  agentStatus.classList.remove("error");
  fetchAgentStatus()
    .then((status) => {
      if (!status.available) {
        throw new Error("Agent offline");
      }
      return runAgentSuggest();
    })
    .catch((error) => {
      agentStatus.textContent = error.message;
      agentStatus.classList.add("error");
      showToast("error", "Agent", error.message);
    });
});

closeEditButton.addEventListener("click", () => {
  editModal.classList.add("hidden");
  activeLiteratureId = null;
});

closeDetailButton.addEventListener("click", () => {
  detailModal.classList.add("hidden");
});

editModal.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) {
    return;
  }
  if (target.dataset.action === "close") {
    editModal.classList.add("hidden");
    activeLiteratureId = null;
  }
});

detailModal.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) {
    return;
  }
  if (target.dataset.action === "close-detail") {
    detailModal.classList.add("hidden");
  }
});

literatureList.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) {
    return;
  }
  const action = target.dataset.action;
  const id = target.dataset.id;
  if (!action || !id) {
    return;
  }

  if (action === "edit") {
    handleEdit(Number(id)).catch(() => {
      literatureList.innerHTML =
        '<div class="table-empty">Update failed.</div>';
    });
  }

  if (action === "view") {
    handleView(Number(id)).catch(() => {
      literatureList.innerHTML =
        '<div class="table-empty">Detail failed.</div>';
    });
  }

  if (action === "delete") {
    handleDelete(Number(id)).catch(() => {
      literatureList.innerHTML =
        '<div class="table-empty">Delete failed.</div>';
    });
  }
});

Promise.all([
  loadStorageRoot(),
  loadAgentConfig(),
  loadCategories(),
  loadLiteratures(),
]).catch(() => {
  statusEl.textContent = "Failed to load storage root";
});
