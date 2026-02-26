const CATALOG = {
  sneakers: [
    {
      id: "snk1",
      name: "Nike Air Max 270",
      price: 15990,
      desc: "Оригинальные Nike Air Max 270. Размеры 36-45.",
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

const cart = {};

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
  const badge = document.getElementById("cartCount");
  badge.textContent = count;
}

function renderCart() {
  const panel = document.getElementById("cartPanel");
  const itemsRoot = document.getElementById("cartItems");
  const totalEl = document.getElementById("cartTotal");

  itemsRoot.innerHTML = "";

  let total = 0;
  Object.entries(cart).forEach(([id, qty]) => {
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
      if (Object.keys(cart).length === 0) {
        panel.classList.add("hidden");
      } else {
        renderCart();
      }
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

function initCartPanel() {
  const cartButton = document.getElementById("cartButton");
  const panel = document.getElementById("cartPanel");
  const close = document.getElementById("closeCart");
  const checkout = document.getElementById("checkoutButton");

  cartButton.onclick = () => {
    if (Object.keys(cart).length === 0) {
      if (window.Telegram?.WebApp) {
        window.Telegram.WebApp.showAlert("Корзина пуста. Добавьте товары.");
      } else {
        alert("Корзина пуста. Добавьте товары.");
      }
      return;
    }
    renderCart();
    panel.classList.remove("hidden");
  };

  close.onclick = () => {
    panel.classList.add("hidden");
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
        })
      );
      window.Telegram.WebApp.showPopup({
        title: "Черновик заказа",
        message: text,
        buttons: [{ id: "ok", type: "default", text: "OK" }],
      });
    } else {
      alert(text);
    }
  };
}

document.addEventListener("DOMContentLoaded", () => {
  initTelegram();
  const initialCategory = "sneakers";
  renderCategories(initialCategory);
  renderProducts(initialCategory);
  updateCartBadge();
  initCartPanel();
});

