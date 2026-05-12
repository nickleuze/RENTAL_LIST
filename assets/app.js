const catalog = document.querySelector('#catalog');
const categoryTabs = document.querySelector('#category-tabs');
const categoryToggle = document.querySelector('#category-toggle');
const searchInput = document.querySelector('#search');
const resultCount = document.querySelector('#result-count');
const emptyState = document.querySelector('#empty-state');

let items = [];
let activeCategory = 'all';

const formatPrice = (value) => {
  if (value === null || value === undefined || value === '') return 'Price on request';
  if (typeof value === 'number') return `${new Intl.NumberFormat('de-DE').format(value)} €`;
  return `${value} €`;
};

const normalize = (value) => String(value || '').toLowerCase();

const itemMatches = (item) => {
  const query = normalize(searchInput.value).trim();
  const haystack = normalize([item.sku, item.name, item.description, item.category].join(' '));
  return (activeCategory === 'all' || item.category === activeCategory) && (!query || haystack.includes(query));
};

const categoryCount = (category) => {
  if (category === 'all') return items.length;
  return items.filter((item) => item.category === category).length;
};

const updateCategoryToggle = () => {
  categoryToggle.textContent = activeCategory === 'all' ? 'Categories: All' : `Categories: ${activeCategory}`;
};

const closeCategoryMenu = () => {
  categoryTabs.classList.remove('is-open');
  categoryToggle.setAttribute('aria-expanded', 'false');
};

const setActiveCategory = (category) => {
  activeCategory = category;

  for (const tab of categoryTabs.querySelectorAll('.tab')) {
    const selected = tab.dataset.category === category;
    tab.classList.toggle('is-active', selected);
    tab.setAttribute('aria-selected', String(selected));
  }

  updateCategoryToggle();
  closeCategoryMenu();
  render();
};

const orderedCategories = (categories, preferredOrder) => {
  const categorySet = new Set(categories);
  const ordered = preferredOrder.filter((category) => categorySet.delete(category));
  return [...ordered, ...Array.from(categorySet).sort((a, b) => a.localeCompare(b))];
};

const renderTabs = (categories) => {
  const allCategories = ['all', ...categories];
  categoryTabs.innerHTML = allCategories.map((category) => {
    const label = category === 'all' ? 'All' : category;
    const selected = category === activeCategory;
    return `
      <button
        class="tab${selected ? ' is-active' : ''}"
        type="button"
        role="tab"
        aria-selected="${selected}"
        data-category="${escapeHtml(category)}"
      >
        <span>${escapeHtml(label)}</span>
        <span class="tab-count">${categoryCount(category)}</span>
      </button>
    `;
  }).join('');

  for (const tab of categoryTabs.querySelectorAll('.tab')) {
    tab.addEventListener('click', () => setActiveCategory(tab.dataset.category));
  }
};

const render = () => {
  const visible = items.filter(itemMatches);
  catalog.innerHTML = visible.map((item) => {
    const hasDescription = Boolean(item.description);
    return `
      <article class="card${hasDescription ? ' has-description' : ''}"${hasDescription ? ' tabindex="0"' : ''}>
        <div class="card-header">
          <h2>${escapeHtml(item.name)}</h2>
          <span class="price">${escapeHtml(formatPrice(item.price_net))}</span>
        </div>
        ${hasDescription ? `<p class="description" role="tooltip">${escapeHtml(item.description)}</p>` : ''}
        <div class="meta">
          ${activeCategory === 'all' ? `<span class="pill">${escapeHtml(item.category)}</span>` : ''}
          <span class="pill">Qty ${escapeHtml(item.quantity)}</span>
        </div>
      </article>
    `;
  }).join('');

  resultCount.textContent = `${visible.length} of ${items.length} items`;
  emptyState.hidden = visible.length !== 0;
};

const escapeHtml = (value) => String(value).replace(/[&<>'"]/g, (char) => ({
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  "'": '&#39;',
  '"': '&quot;',
}[char]));

const loadJson = async (url) => {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
};

const loadCategoryOrder = async () => {
  try {
    const order = await loadJson('data/category-order.json');
    return Array.isArray(order) ? order : [];
  } catch (error) {
    console.warn(`Category order not loaded: ${error.message}`);
    return [];
  }
};

const loadCatalog = async () => {
  try {
    const [data, preferredOrder] = await Promise.all([
      loadJson('data/inventory.json'),
      loadCategoryOrder(),
    ]);
    items = data.items || [];

    renderTabs(orderedCategories(data.categories || [], preferredOrder));
    updateCategoryToggle();
    render();
  } catch (error) {
    resultCount.textContent = 'Could not load catalog data.';
    emptyState.hidden = false;
    emptyState.textContent = `Catalog load failed: ${error.message}`;
  }
};

categoryToggle.addEventListener('click', () => {
  const isOpen = categoryTabs.classList.toggle('is-open');
  categoryToggle.setAttribute('aria-expanded', String(isOpen));
});

searchInput.addEventListener('input', render);

loadCatalog();
