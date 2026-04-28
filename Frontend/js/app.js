const apiBase = "http://127.0.0.1:8000";

const storageRootInput = document.getElementById("storageRoot");
const saveRootButton = document.getElementById("saveRoot");
const statusEl = document.getElementById("rootStatus");
const healthButton = document.getElementById("healthCheck");
const healthResult = document.getElementById("healthResult");

const uploadForm = document.getElementById("uploadForm");
const titleInput = document.getElementById("titleInput");
const authorsInput = document.getElementById("authorsInput");
const yearInput = document.getElementById("yearInput");
const journalInput = document.getElementById("journalInput");
const abstractInput = document.getElementById("abstractInput");
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
const editCategory = document.getElementById("editCategory");
const saveEditButton = document.getElementById("saveEdit");
const agentSuggestButton = document.getElementById("agentSuggest");
const agentStatus = document.getElementById("agentStatus");

let categoryMap = new Map();
let literatureCache = new Map();
let activeLiteratureId = null;

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
}

async function pingApi() {
  const data = await fetchJson(`${apiBase}/`);
  healthResult.textContent = JSON.stringify(data, null, 2);
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
        <button class="ghost" data-action="edit" data-id="${item.id}">Edit</button>
        <button data-action="delete" data-id="${item.id}">Delete</button>
      </div>
    `;
    literatureList.appendChild(row);
  });
}

async function loadLiteratures() {
  const data = await fetchJson(`${apiBase}/literatures`);
  renderLiteratures(data);
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
  editCategory.value = item.category_id || "";
  agentStatus.textContent = "";
  editModal.classList.remove("hidden");
}

async function handleDelete(literatureId) {
  const ok = window.confirm("Delete this literature item?");
  if (!ok) {
    return;
  }
  await deleteLiterature(literatureId);
  await loadLiteratures();
}

async function fetchAgentStatus() {
  const data = await fetchJson(`${apiBase}/agent/status`);
  return data;
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
}

async function runSearch() {
  const params = new URLSearchParams();
  if (searchInput.value.trim()) params.set("q", searchInput.value.trim());
  if (searchCategory.value) params.set("category_id", searchCategory.value);
  if (yearStartInput.value) params.set("year_start", yearStartInput.value);
  if (yearEndInput.value) params.set("year_end", yearEndInput.value);

  const query = params.toString();
  const url = query ? `${apiBase}/search?${query}` : `${apiBase}/search`;
  const data = await fetchJson(url);
  renderLiteratures(data);
}

async function handleUpload(event) {
  event.preventDefault();
  uploadStatus.textContent = "";

  const file = fileInput.files[0];
  if (!file) {
    uploadStatus.textContent = "Please choose a file.";
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  if (titleInput.value) formData.append("title", titleInput.value);
  if (authorsInput.value) formData.append("authors", authorsInput.value);
  if (yearInput.value) formData.append("year", yearInput.value);
  if (journalInput.value) formData.append("journal", journalInput.value);
  if (abstractInput.value) formData.append("abstract", abstractInput.value);
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
        reject(new Error("Upload failed"));
      }
    });
    xhr.addEventListener("error", () => reject(new Error("Upload failed")));
    xhr.send(formData);
  });

  uploadStatus.textContent = "Upload complete.";
  uploadForm.reset();
  await loadLiteratures();
  uploadProgress.style.width = "0%";
}

saveRootButton.addEventListener("click", () => {
  saveStorageRoot().catch((error) => {
    statusEl.textContent = error.message;
  });
});

healthButton.addEventListener("click", () => {
  pingApi().catch(() => {
    healthResult.textContent = "Ping failed";
  });
});

uploadForm.addEventListener("submit", (event) => {
  handleUpload(event).catch((error) => {
    uploadStatus.textContent = error.message;
    uploadStatus.classList.add("error");
  });
});

refreshListButton.addEventListener("click", () => {
  loadLiteratures().catch(() => {
    literatureList.innerHTML =
      '<div class="table-empty">Failed to load list.</div>';
  });
});

runSearchButton.addEventListener("click", () => {
  runSearch().catch(() => {
    literatureList.innerHTML = '<div class="table-empty">Search failed.</div>';
  });
});

addCategoryButton.addEventListener("click", () => {
  const name = newCategoryInput.value.trim();
  if (!name) {
    categoryStatus.textContent = "Please enter a category name.";
    categoryStatus.classList.add("error");
    return;
  }
  createCategory(name)
    .then(() => {
      categoryStatus.textContent = "Category added.";
      categoryStatus.classList.remove("error");
      newCategoryInput.value = "";
      return loadCategories();
    })
    .catch((error) => {
      categoryStatus.textContent = error.message;
      categoryStatus.classList.add("error");
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
      });
  }

  if (action === "delete") {
    const ok = window.confirm("Delete this category?");
    if (!ok) {
      return;
    }
    deleteCategory(Number(id))
      .then(() => loadCategories())
      .catch((error) => {
        categoryStatus.textContent = error.message;
        categoryStatus.classList.add("error");
      });
  }
});

saveEditButton.addEventListener("click", () => {
  if (!activeLiteratureId) {
    return;
  }
  const payload = {
    title: editTitle.value.trim() || null,
    authors: editAuthors.value.trim() || null,
    year: editYear.value ? Number(editYear.value) : null,
    journal: editJournal.value.trim() || null,
    abstract: editAbstract.value.trim() || null,
    category_id: editCategory.value ? Number(editCategory.value) : null,
  };
  updateLiterature(activeLiteratureId, payload)
    .then(() => {
      editModal.classList.add("hidden");
      return loadLiteratures();
    })
    .catch(() => {
      agentStatus.textContent = "Update failed.";
      agentStatus.classList.add("error");
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
    });
});

closeEditButton.addEventListener("click", () => {
  editModal.classList.add("hidden");
  activeLiteratureId = null;
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

  if (action === "delete") {
    handleDelete(Number(id)).catch(() => {
      literatureList.innerHTML =
        '<div class="table-empty">Delete failed.</div>';
    });
  }
});

Promise.all([loadStorageRoot(), loadCategories(), loadLiteratures()]).catch(
  () => {
    statusEl.textContent = "Failed to load storage root";
  },
);
