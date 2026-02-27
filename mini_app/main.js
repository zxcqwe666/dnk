const BOT_URL = "https://t.me/dnkstock_bot";

const CATALOG = {
  sneakers: [
    {
      id: "snk1",
      name: "Rick Owens Performa",
      price: 500,
      desc: "Размеры 36-45.",
      emoji: "👟",
    },
    {
      id: "snk2",
      name: "Adidas Yeezy Boost 350",
      price: 24990,
      desc: "Adidas Yeezy Boost 350 V2. Лимитированная коллекция.",
      emoji: "🌀",
    },
  ],
  clothes: [
    {
      id: "cl1",
      name: "Худи Essentials",
      price: 7990,
      desc: "Уютное худи oversize. Размеры XS-XL.",
      emoji: "🧥",
    },
    {
      id: "cl2",
      name: "Футболка Basic",
      price: 2990,
      desc: "Базовая хлопковая футболка, много цветов.",
      emoji: "👕",
    },
  ],
};

const CATEGORIES = {
  sneakers: "Кроссовки",
  clothes: "Одежда",
};

let cart = {};
let profile = {
  shoe_size: "",
  clothing_size: "",
  city: "",
  delivery: "",
  phone: "",
};

const BY_CITIES = [
  "минск",
  "брест",
  "витебск",
  "гродно",
  "гомель",
  "могилёв",
  "могилев",
  "барановичи",
  "бобруйск",
  "борисов",
  "лида",
  "молодечно",
  "орша",
  "пинск",
  "полоцк",
  "новополоцк",
  "солигорск",
  "мозырь",
];

const DELIVERY_OPTIONS = ["Личная встреча", "Европочта", "Белпочта"];

function formatPrice(value) {
  return value.toLocaleString("ru-RU") + " ₽";
}

function initTelegram() {
  if (!window.Telegram || !window.Telegram.WebApp) {
    return;
  }
  const tg = window.Telegram.WebApp;
  tg.expand();
  tg.setHeaderColor("#0f1115");
  tg.setBackgroundColor("#050509");
}

function initQrPanel() {
  const btn = document.getElementById("qrButton");
  const panel = document.getElementById("qrPanel");
  const close = document.getElementById("closeQr");
  const img = document.getElementById("qrImage");

  if (img) {
    const url = `https://api.qrserver.com/v1/create-qr-code/?size=256x256&data=${encodeURIComponent(
      BOT_URL
    )}`;
    img.src = url;
  }

  if (btn) {
    btn.onclick = () => {
      panel.classList.remove("hidden");
    };
  }
  if (close) {
    close.onclick = () => {
      panel.classList.add("hidden");
    };
  }
}

function loadProfileFromStorage() {
  try {
    const raw = localStorage.getItem("dnk_profile_v1");
    if (!raw) return;
    const data = JSON.parse(raw);
    profile = { ...profile, ...data };
  } catch (_) {}
}

function saveProfileToStorage() {
  try {
    localStorage.setItem("dnk_profile_v1", JSON.stringify(profile));
  } catch (_) {}
}

function normalizePhone(raw) {
  return raw.replace(/[^\d+]/g, "");
}

function isValidBelarusPhone(raw) {
  let p = normalizePhone(raw);
  if (!p) return false;
  if (p.startsWith("+")) {
    p = p.slice(1);
  }
  if (p.startsWith("80")) {
    p = "375" + p.slice(2);
  }
  if (!p.startsWith("375")) return false;
  const rest = p.slice(3);
  if (!/^(25|29|33|44|17)\d{7}$/.test(rest)) {
    return false;
  }
  return true;
}

function renderCategories(activeId) {
  const chips = document.getElementById("categoryChips");
  chips.innerHTML = "";

  Object.entries(CATEGORIES).forEach(([id, title]) => {
    const chip = document.createElement("button");
    chip.className = "chip" + (id === activeId ? " active" : "");
    chip.textContent = title;
    chip.onclick = () => {
      renderCategories(id);
      renderProducts(id);
    };
    chips.appendChild(chip);
  });
}

function renderProducts(categoryId) {
  const grid = document.getElementById("productGrid");
  const title = document.getElementById("productsTitle");
  title.textContent = CATEGORIES[categoryId] || "Товары";

  grid.innerHTML = "";
  const products = CATALOG[categoryId] || [];

  products.forEach((p) => {
    const card = document.createElement("div");
    card.className = "product-card";

    const img = document.createElement("div");
    img.className = "product-image";
    img.textContent = p.emoji || "⭐";

    const name = document.createElement("div");
    name.className = "product-name";
    name.textContent = p.name;

    const desc = document.createElement("div");
    desc.className = "product-desc";
    desc.textContent = p.desc;

    const footer = document.createElement("div");
    footer.className = "product-footer";

    const price = document.createElement("div");
    price.className = "price";
    price.textContent = formatPrice(p.price);

    const button = document.createElement("button");
    button.className = "secondary-button";
    button.textContent = "В корзину";
    button.onclick = () => {
      cart[p.id] = (cart[p.id] || 0) + 1;
      updateCartBadge();
      if (window.Telegram?.WebApp) {
        window.Telegram.WebApp.HapticFeedback.impactOccurred("medium");
      }
    };

    footer.appendChild(price);
    footer.appendChild(button);

    card.appendChild(img);
    card.appendChild(name);
    card.appendChild(desc);
    card.appendChild(footer);

    grid.appendChild(card);
  });
}

function updateCartBadge() {
  const count = Object.values(cart).reduce((sum, qty) => sum + qty, 0);
  const badge = document.getElementById("cartBadge");
  if (badge) badge.textContent = count;
}

function renderCart() {
  const panel = document.getElementById("cartPanel");
  const itemsRoot = document.getElementById("cartItems");
  const totalEl = document.getElementById("cartTotal");
  const emptyEl = document.getElementById("cartEmpty");

  itemsRoot.innerHTML = "";

  let total = 0;
  const entries = Object.entries(cart);
  if (entries.length === 0) {
    if (emptyEl) emptyEl.classList.remove("hidden");
    totalEl.textContent = formatPrice(0);
    return;
  }
  if (emptyEl) emptyEl.classList.add("hidden");
  entries.forEach(([id, qty]) => {
    let product =
      CATALOG.sneakers.find((p) => p.id === id) ||
      CATALOG.clothes.find((p) => p.id === id);
    if (!product) return;

    const lineTotal = product.price * qty;
    total += lineTotal;

    const row = document.createElement("div");
    row.className = "cart-item";

    const main = document.createElement("div");
    main.className = "cart-item-main";

    const name = document.createElement("div");
    name.className = "cart-item-name";
    name.textContent = product.name;

    const meta = document.createElement("div");
    meta.className = "cart-item-meta";
    meta.textContent = `${qty} × ${formatPrice(product.price)}`;

    main.appendChild(name);
    main.appendChild(meta);

    const qtyBox = document.createElement("div");
    qtyBox.className = "cart-item-qty";

    const minus = document.createElement("button");
    minus.className = "qty-button";
    minus.textContent = "−";
    minus.onclick = () => {
      if (cart[id] > 1) {
        cart[id] -= 1;
      } else {
        delete cart[id];
      }
      updateCartBadge();
      renderCart();
    };

    const qtyLabel = document.createElement("span");
    qtyLabel.textContent = qty;

    const plus = document.createElement("button");
    plus.className = "qty-button";
    plus.textContent = "+";
    plus.onclick = () => {
      cart[id] = (cart[id] || 0) + 1;
      updateCartBadge();
      renderCart();
    };

    qtyBox.appendChild(minus);
    qtyBox.appendChild(qtyLabel);
    qtyBox.appendChild(plus);

    row.appendChild(main);
    row.appendChild(qtyBox);

    itemsRoot.appendChild(row);
  });

  totalEl.textContent = formatPrice(total);
}

window.renderCart = renderCart;

function initCartPanel() {
  const tabCart = document.getElementById("tabCart");
  const panel = document.getElementById("cartPanel");
  const close = document.getElementById("closeCart");
  const checkout = document.getElementById("checkoutButton");

  if (tabCart) {
    tabCart.onclick = () => {
      if (typeof window.setActiveTab === "function") {
        window.setActiveTab("cart");
      } else {
        renderCart();
        panel.classList.remove("hidden");
      }
    };
  }

  close.onclick = () => {
    if (typeof window.setActiveTab === "function") {
      window.setActiveTab("catalog");
    } else {
      panel.classList.add("hidden");
    }
  };

  checkout.onclick = () => {
    if (Object.keys(cart).length === 0) {
      return;
    }

    const lines = [];
    let total = 0;

    Object.entries(cart).forEach(([id, qty]) => {
      let product =
        CATALOG.sneakers.find((p) => p.id === id) ||
        CATALOG.clothes.find((p) => p.id === id);
      if (!product) return;
      const lineTotal = product.price * qty;
      total += lineTotal;
      lines.push(
        `${product.name} — ${qty} шт. × ${formatPrice(product.price)} = ${formatPrice(
          lineTotal
        )}`
      );
    });

    lines.push(`\nИтого: ${formatPrice(total)}`);
    lines.push(
      "\nОтправьте этот заказ менеджеру в чат, указав ваш размер, город и способ доставки."
    );

    const text = lines.join("\n");

    if (window.Telegram?.WebApp) {
      window.Telegram.WebApp.sendData(
        JSON.stringify({
          type: "order",
          items: cart,
          total,
          profile,
        })
      );
      window.Telegram.WebApp.showPopup({
        title: "Заказ оформлен",
        message: text,
        buttons: [{ id: "ok", type: "default", text: "OK" }],
      });
      cart = {};
      updateCartBadge();
      renderCart();
      if (typeof window.setActiveTab === "function") {
        window.setActiveTab("catalog");
      } else {
        panel.classList.add("hidden");
      }
    } else {
      alert(text);
      cart = {};
      updateCartBadge();
      renderCart();
      panel.classList.add("hidden");
    }
  };
}

function initProfilePanel() {
  const tabProfile = document.getElementById("tabProfile");
  const tabCatalog = document.getElementById("tabCatalog");
  const tabSearch = document.getElementById("tabSearch");
  const tabCart = document.getElementById("tabCart");

  const panel = document.getElementById("profilePanel");
  const searchPanel = document.getElementById("searchPanel");
  const cartPanel = document.getElementById("cartPanel");

  const close = document.getElementById("closeProfile");
  const save = document.getElementById("saveProfileButton");
  const myOrders = document.getElementById("myOrdersButton");

  const closeSearch = document.getElementById("closeSearch");
  const searchInput = document.getElementById("searchQuery");
  const searchResults = document.getElementById("searchResults");

  const shoeInput = document.getElementById("shoeSize");
  const clothingInput = document.getElementById("clothingSize");
  const cityInput = document.getElementById("city");
  const deliveryInput = document.getElementById("delivery");
  const phoneInput = document.getElementById("phone");

  const shoeError = document.getElementById("shoeError");
  const clothingError = document.getElementById("clothingError");
  const cityError = document.getElementById("cityError");
  const deliveryError = document.getElementById("deliveryError");
  const phoneError = document.getElementById("phoneError");

  const setActiveTab = (tab) => {
    [tabCatalog, tabSearch, tabCart, tabProfile].forEach((btn) => {
      if (btn) btn.classList.remove("bottom-nav-item--active");
    });
    panel.classList.add("hidden");
    searchPanel.classList.add("hidden");
    cartPanel.classList.add("hidden");

    if (tab === "catalog") {
      tabCatalog.classList.add("bottom-nav-item--active");
    } else if (tab === "search") {
      tabSearch.classList.add("bottom-nav-item--active");
      searchPanel.classList.remove("hidden");
    } else if (tab === "cart") {
      if (tabCart) tabCart.classList.add("bottom-nav-item--active");
      cartPanel.classList.remove("hidden");
      if (typeof window.renderCart === "function") {
        window.renderCart();
      }
    } else if (tab === "profile") {
      tabProfile.classList.add("bottom-nav-item--active");
      panel.classList.remove("hidden");
    }
  };

  window.setActiveTab = setActiveTab;

  const clearErrors = () => {
    [
      [shoeInput, shoeError],
      [clothingInput, clothingError],
      [cityInput, cityError],
      [deliveryInput, deliveryError],
      [phoneInput, phoneError],
    ].forEach(([input, errorEl]) => {
      input.classList.remove("invalid");
      errorEl.textContent = "";
    });
  };

  const applyToInputs = () => {
    shoeInput.value = profile.shoe_size || "";
    clothingInput.value = profile.clothing_size || "";
    cityInput.value = profile.city || "Минск";
    deliveryInput.value = profile.delivery || "Личная встреча";
    phoneInput.value = profile.phone || "";
  };

  tabProfile.onclick = () => {
    applyToInputs();
    setActiveTab("profile");
  };

  tabCatalog.onclick = () => {
    setActiveTab("catalog");
  };

  if (tabCart) {
    tabCart.onclick = () => {
      setActiveTab("cart");
    };
  }

  const allProducts = [...CATALOG.sneakers, ...CATALOG.clothes];

  const renderSearchResults = (query) => {
    const q = query.trim().toLowerCase();
    searchResults.innerHTML = "";
    const filtered = q
      ? allProducts.filter(
          (p) =>
            p.name.toLowerCase().includes(q) ||
            p.desc.toLowerCase().includes(q)
        )
      : allProducts;

    filtered.forEach((p) => {
      const card = document.createElement("div");
      card.className = "product-card";

      const img = document.createElement("div");
      img.className = "product-image";
      img.textContent = p.emoji || "⭐";

      const name = document.createElement("div");
      name.className = "product-name";
      name.textContent = p.name;

      const desc = document.createElement("div");
      desc.className = "product-desc";
      desc.textContent = p.desc;

      const footer = document.createElement("div");
      footer.className = "product-footer";

      const price = document.createElement("div");
      price.className = "price";
      price.textContent = formatPrice(p.price);

      const button = document.createElement("button");
      button.className = "secondary-button";
      button.textContent = "В корзину";
      button.onclick = () => {
        cart[p.id] = (cart[p.id] || 0) + 1;
        updateCartBadge();
        if (window.Telegram?.WebApp) {
          window.Telegram.WebApp.HapticFeedback.impactOccurred("medium");
        }
      };

      footer.appendChild(price);
      footer.appendChild(button);

      card.appendChild(img);
      card.appendChild(name);
      card.appendChild(desc);
      card.appendChild(footer);

      searchResults.appendChild(card);
    });
  };

  tabSearch.onclick = () => {
    setActiveTab("search");
    renderSearchResults(searchInput.value || "");
    searchInput.focus();
  };

  deliveryInput.addEventListener("change", () => {
    const value = deliveryInput.value;
    if (value === "Личная встреча") {
      cityInput.value = "Брест";
      cityInput.disabled = true;
    } else {
      cityInput.disabled = false;
      if (!profile.city) {
        cityInput.value = "Минск";
      }
    }
  });

  close.onclick = () => {
    setActiveTab("catalog");
  };

  closeSearch.onclick = () => {
    setActiveTab("catalog");
  };

  searchInput.addEventListener("input", (e) => {
    renderSearchResults(e.target.value);
  });

  save.onclick = () => {
    clearErrors();

    const shoe = shoeInput.value.trim();
    const clothing = clothingInput.value.trim();
    const city = cityInput.value.trim();
    const delivery = deliveryInput.value.trim();
    const phone = phoneInput.value.trim();

    let hasError = false;

    const shoeNum = parseFloat(shoe.replace(",", "."));
    if (!shoe || Number.isNaN(shoeNum) || shoeNum < 34 || shoeNum > 50) {
      shoeInput.classList.add("invalid");
      shoeError.textContent = "Укажите размер от 34 до 50.";
      hasError = true;
    }

    const clothingUpper = clothing.toUpperCase();
    const clothingOk =
      /^(XS|S|M|L|XL|XXL|XXXL)$/.test(clothingUpper) ||
      (/^\d{2}$/.test(clothing) && Number(clothing) >= 40 && Number(clothing) <= 60);
    if (!clothing || !clothingOk) {
      clothingInput.classList.add("invalid");
      clothingError.textContent = "Например: M, L, XL или размер 44–58.";
      hasError = true;
    }

    const cityNorm = city.toLowerCase();
    if (!city || !BY_CITIES.includes(cityNorm)) {
      cityInput.classList.add("invalid");
      cityError.textContent = "Выберите один из городов Беларуси из списка.";
      hasError = true;
    }

    if (!delivery || !DELIVERY_OPTIONS.includes(delivery)) {
      deliveryInput.classList.add("invalid");
      deliveryError.textContent = "Выберите способ доставки из списка.";
      hasError = true;
    }

    if (!phone || !isValidBelarusPhone(phone)) {
      phoneInput.classList.add("invalid");
      phoneError.textContent = "Телефон в формате Беларуси, например +375 29 123 45 67.";
      hasError = true;
    }

    if (hasError) {
      if (window.Telegram?.WebApp) {
        window.Telegram.WebApp.showAlert("Проверьте данные профиля и исправьте ошибки.");
      } else {
        alert("Проверьте данные профиля и исправьте ошибки.");
      }
      return;
    }

    profile = {
      shoe_size: shoe,
      clothing_size: clothing,
      city,
      delivery,
      phone,
    };
    saveProfileToStorage();

    if (window.Telegram?.WebApp) {
      window.Telegram.WebApp.sendData(
        JSON.stringify({
          type: "profile",
          profile,
        })
      );
      window.Telegram.WebApp.showPopup({
        title: "Профиль сохранён",
        message: "Мы будем подставлять эти данные в заказы.",
        buttons: [{ id: "ok", type: "default", text: "OK" }],
      });
    }

    panel.classList.add("hidden");
  };

  if (myOrders) {
    myOrders.onclick = () => {
      if (window.Telegram?.WebApp) {
        window.Telegram.WebApp.sendData(
          JSON.stringify({
            type: "myorders",
          })
        );
        window.Telegram.WebApp.showPopup({
          title: "Заказы отправлены",
          message: "Мы отправили ваши заказы в чат с ботом.",
          buttons: [{ id: "ok", type: "default", text: "OK" }],
        });
      } else {
        alert("Откройте в Telegram, чтобы посмотреть заказы.");
      }
    };
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initTelegram();
  initQrPanel();
  loadProfileFromStorage();
  const initialCategory = "sneakers";
  renderCategories(initialCategory);
  renderProducts(initialCategory);
  updateCartBadge();
  initCartPanel();
  initProfilePanel();
});

