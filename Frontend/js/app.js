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

let categoryMap = new Map();

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
  data.forEach((category) => {
    const option = document.createElement("option");
    option.value = category.id;
    option.textContent = category.name;
    categorySelect.appendChild(option);
    const searchOption = document.createElement("option");
    searchOption.value = category.id;
    searchOption.textContent = category.name;
    searchCategory.appendChild(searchOption);
  });
}

function renderLiteratures(items) {
  literatureList.innerHTML = "";
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
    `;
    literatureList.appendChild(row);
  });
}

async function loadLiteratures() {
  const data = await fetchJson(`${apiBase}/literatures`);
  renderLiteratures(data);
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
  await fetchJson(`${apiBase}/literatures/upload`, {
    method: "POST",
    body: formData,
  });

  uploadStatus.textContent = "Upload complete.";
  uploadForm.reset();
  await loadLiteratures();
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

Promise.all([loadStorageRoot(), loadCategories(), loadLiteratures()]).catch(
  () => {
    statusEl.textContent = "Failed to load storage root";
  },
);
