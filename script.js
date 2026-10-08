const tg = window.Telegram?.WebApp;
if(tg) {
    tg.expand();
    if (tg.disableVerticalSwipes) {
        tg.disableVerticalSwipes();
    }
}

const products = [
    { id: 1, name: "Трайфл «Банан-Клубника»", price: 1500, img: "banan.jpg" },
    { id: 2, name: "Трайфл «Вишня с шоколадом»", price: 1500, img: "vishny.jpg" },
    { id: 3, name: "Трайфл «Клубника»", price: 1500, img: "klubnika.jpg" }
];

let cart = {};
let isCartBtnVisible = false;
let saturdaysData = [];

function initTelegramData() {
    const tgUser = tg?.initDataUnsafe?.user || {};
    const nameInput = document.getElementById('username');
    const nameGroup = document.getElementById('name-input-group');
    
    if (nameInput) {
        if (tgUser.first_name) nameInput.value = tgUser.first_name;
        const accountText = document.createElement('p');
        accountText.className = 'tg-account-info';
        accountText.innerText = tgUser.username ? 
            `👤 Аккаунт для связи: @${tgUser.username}` : 
            `👤 Аккаунт Telegram успешно привязан к заказу`;
        nameGroup.appendChild(accountText);
    }
}

function renderProducts() {
    const container = document.getElementById('products-container');
    products.forEach((p, index) => {
        const card = document.createElement('div');
        card.className = 'product-card animate__animated animate__fadeInUp';
        card.style.animationDelay = `${index * 0.1}s`; 
        
        card.innerHTML = `
            <img src="${p.img}" class="product-image" alt="${p.name}">
            <div class="product-info-wrap">
                <div class="product-info">
                    <h3>${p.name}</h3>
                    <p>${p.price} ₽</p>
                </div>
                <div class="action-container" id="control-${p.id}">
                    <button class="add-btn" id="btn-add-${p.id}" onclick="handleFirstAdd(event, ${p.id})">В корзину</button>
                    <div class="counter-ui" id="counter-ui-${p.id}">
                        <button class="counter-btn minus" onclick="handleMinus(event, ${p.id})">–</button>
                        <div class="count-wrapper"><span class="count-text" id="count-${p.id}">1</span></div>
                        <button class="counter-btn plus" onclick="handlePlus(event, ${p.id})">+</button>
                    </div>
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

function handleFirstAdd(event, id) {
    if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('medium');
    
    const btn = event.currentTarget;
    gsap.fromTo(btn, { scale: 0.92 }, { scale: 1, duration: 0.4, ease: "back.out(2)" });
    
    const rect = btn.getBoundingClientRect();
    const x = (rect.left + rect.width / 2) / window.innerWidth;
    const y = (rect.top + rect.height / 2) / window.innerHeight;

    confetti({
        particleCount: 16, spread: 45, startVelocity: 18, scalar: 0.9, ticks: 60,
        origin: { x, y }, colors: ['#FFD700', '#FFA500', '#FF69B4', '#FFFFFF'], shapes: ['star', 'circle'], zIndex: 9999
    });

    cart[id] = 1;
    updateCartUI();

    const counter = document.getElementById(`counter-ui-${id}`);
    gsap.to(btn, { opacity: 0, duration: 0.2, onComplete: () => btn.classList.add('hidden') });
    gsap.fromTo(counter, { opacity: 0, scale: 0.8 }, { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(1.5)", delay: 0.1 });
    counter.classList.add('active');
    document.getElementById(`count-${id}`).innerText = cart[id];
}

function handlePlus(event, id) {
    if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('light');
    cart[id]++;
    updateCounterNum(id, 1);
    updateCartUI();
}

function handleMinus(event, id) {
    if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('light');
    cart[id]--;
    
    if (cart[id] === 0) {
        const btn = document.getElementById(`btn-add-${id}`);
        const counter = document.getElementById(`counter-ui-${id}`);
        
        gsap.to(counter, { opacity: 0, scale: 0.8, duration: 0.2, onComplete: () => counter.classList.remove('active') });
        btn.classList.remove('hidden');
        gsap.to(btn, { opacity: 1, duration: 0.2, delay: 0.1 });
    } else {
        updateCounterNum(id, -1);
    }
    updateCartUI();
}

function updateCounterNum(id, direction) {
    const el = document.getElementById(`count-${id}`);
    if (el) {
        const yOffset = direction > 0 ? 15 : -15;
        gsap.to(el, { y: -yOffset, opacity: 0, duration: 0.15, onComplete: () => {
            el.innerText = cart[id];
            gsap.fromTo(el, { y: yOffset, opacity: 0 }, { y: 0, opacity: 1, duration: 0.3, ease: "back.out(2)" });
        }});
    }
}

function updateCartUI() {
    let totalCount = 0;
    let totalPrice = 0;
    
    for (let id in cart) {
        if (cart[id] > 0) {
            const product = products.find(p => p.id == id);
            totalCount += cart[id];
            totalPrice += product.price * cart[id];
        }
    }
    
    const floatingBtn = document.getElementById('floating-cart-btn');
    document.getElementById('cart-total-count').innerText = totalCount;
    
    if (totalCount > 0 && !isCartBtnVisible) {
        floatingBtn.style.display = 'block';
        gsap.fromTo(floatingBtn, { y: 100, opacity: 0 }, { y: 0, opacity: 1, duration: 0.4, ease: "back.out(1.5)" });
        isCartBtnVisible = true;
    } else if (totalCount === 0 && isCartBtnVisible) {
        gsap.to(floatingBtn, { y: 100, opacity: 0, duration: 0.3, onComplete: () => { floatingBtn.style.display = 'none'; } });
        isCartBtnVisible = false;
    }
    
    if (document.getElementById('cart-screen').classList.contains('active')) {
        renderCartSheet(totalPrice, totalCount);
    }
}

function renderCartSheet(totalPrice, totalCount) {
    const filledContent = document.getElementById('cart-content-filled');
    const emptyContent = document.getElementById('cart-content-empty');
    const headerBtn = document.getElementById('clear-cart-btn');

    if (totalCount === 0) {
        filledContent.style.display = 'none';
        emptyContent.style.setProperty('display', 'flex', 'important');
        headerBtn.style.display = 'none';
        if(tg?.MainButton) tg.MainButton.hide();
        return;
    }

    filledContent.style.display = 'block';
    emptyContent.style.setProperty('display', 'none', 'important');
    headerBtn.style.display = 'block';

    const list = document.getElementById('cart-items-list');
    list.innerHTML = '';
    for (let id in cart) {
        if (cart[id] > 0) {
            const p = products.find(p => p.id == id);
            list.innerHTML += `
                <div class="cart-item">
                    <img src="${p.img}" class="cart-item-img">
                    <div class="cart-item-info">
                        <div class="cart-item-title">${p.name}</div>
                        <div class="cart-item-price">${p.price} ₽</div>
                    </div>
                    <div class="cart-item-controls">
                        <button class="counter-btn minus" onclick="handleMinus(event, ${p.id})">–</button>
                        <span class="count-text">${cart[id]}</span>
                        <button class="counter-btn plus" onclick="handlePlus(event, ${p.id})">+</button>
                    </div>
                </div>
            `;
        }
    }
    
    document.getElementById('cart-subtotal').innerText = `${totalPrice} ₽`;
    document.getElementById('cart-grandtotal').innerText = `${totalPrice} ₽`;
    document.getElementById('checkout-total').innerText = `Сумма: ${totalPrice} ₽`;
    
    if(tg?.MainButton) tg.MainButton.setText(`Оплатить ${totalPrice} ₽`);
}

function clearCart(event) {
    if (event) event.preventDefault();
    if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('medium');
    
    cart = {};
    products.forEach(p => {
        const btn = document.getElementById(`btn-add-${p.id}`);
        const counter = document.getElementById(`counter-ui-${p.id}`);
        if(counter && counter.classList.contains('active')) {
            gsap.to(counter, { opacity: 0, scale: 0.8, duration: 0.2, onComplete: () => {
                counter.classList.remove('active');
            }});
            btn.classList.remove('hidden');
            gsap.to(btn, { opacity: 1, duration: 0.2, delay: 0.1 });
        }
    });
    
    updateCartUI();
}

function openCartSheet() {
    document.getElementById('overlay').classList.add('active');
    document.getElementById('cart-screen').classList.add('active');
    gsap.set('#cart-screen', { y: 0 }); 
    gsap.to('#floating-cart-btn', { y: 100, opacity: 0, duration: 0.3 });
    
    let totalPrice = 0;
    let totalCount = 0;
    for (let id in cart) {
        if (cart[id] > 0) {
            totalPrice += products.find(p => p.id == id).price * cart[id];
            totalCount += cart[id];
        }
    }
    renderCartSheet(totalPrice, totalCount);
}

function closeCartWithHaptic() {
    if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
    }
    const cartSheet = document.getElementById('cart-screen');
    cartSheet.classList.remove('active');
    gsap.to(cartSheet, { y: "100%", duration: 0.4, ease: "power2.inOut", onComplete: () => {
        closeAllSheets();
    }});
}

function goToCheckout() {
    document.getElementById('cart-screen').classList.remove('active');
    document.getElementById('checkout-screen').classList.add('active');
    gsap.set('#checkout-screen', { y: 0 });
    
    if(tg?.MainButton) {
        tg.MainButton.color = "#1A1A1A"; 
        tg.MainButton.show();
        tg.MainButton.onClick(sendDataToBot);
    }
}

function closeAllSheets() {
    document.getElementById('overlay').classList.remove('active');
    document.getElementById('cart-screen').classList.remove('active');
    document.getElementById('checkout-screen').classList.remove('active');
    
    if (isCartBtnVisible) {
        gsap.to('#floating-cart-btn', { y: 0, opacity: 1, duration: 0.4, ease: "back.out(1.5)" });
    }
    if(tg?.MainButton) tg.MainButton.hide();
}

function sendDataToBot() {
    const tgUser = window.Telegram?.WebApp?.initDataUnsafe?.user || {};
    
    const address = {
        street: document.getElementById('street').value,
        house: document.getElementById('house').value,
        entrance: document.getElementById('entrance').value,
        floor: document.getElementById('floor').value,
        flat: document.getElementById('flat').value,
        comment: document.getElementById('comment').value
    };
    const phone = document.getElementById('phone').value;
    const name = document.getElementById('username').value;
    
    let deliveryTime = document.getElementById('delivery-time-value').innerText;
    if (deliveryTime.includes('Указать...')) deliveryTime = "Не выбрано";

    let cartData = [];
    let totalPrice = 0;
    for (let id in cart) {
        if (cart[id] > 0) {
            const p = products.find(p => p.id == id);
            cartData.push({ id: p.id, name: p.name, quantity: cart[id], price: p.price });
            totalPrice += p.price * cart[id];
        }
    }

    const payload = { 
        cart: cartData, 
        totalPrice: totalPrice, 
        address: address, 
        phone: phone, 
        name: name,
        delivery_time: deliveryTime,
        tg_username: tgUser.username || "Скрыт",
        tg_id: tgUser.id || "Неизвестен"
    };
    
    if(tg) {
        tg.sendData(JSON.stringify(payload));
        tg.close();
    }
}

function initBottomSheetSwipe(sheetId, handleAreaId) {
    const sheet = document.getElementById(sheetId);
    const handleArea = document.getElementById(handleAreaId);
    
    let startY = 0;
    let currentY = 0;
    let isDragging = false;

    function onDragStart(e) {
        startY = e.type.includes('mouse') ? e.clientY : e.touches[0].clientY;
        isDragging = true;
        sheet.style.transition = 'none'; 
    }
    function onDragMove(e) {
        if (!isDragging) return;
        const y = e.type.includes('mouse') ? e.clientY : e.touches[0].clientY;
        currentY = Math.max(0, y - startY); 
        gsap.set(sheet, { y: currentY });
    }
    function onDragEnd() {
        if (!isDragging) return;
        isDragging = false;
        
        const threshold = sheet.offsetHeight * 0.20;
        
        if (currentY > threshold) {
            if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
            gsap.to(sheet, { y: "100%", duration: 0.3, ease: "power2.out", onComplete: () => {
                gsap.set(sheet, { clearProps: "all" });
                closeAllSheets(); 
            }});
        } else {
            gsap.to(sheet, { y: 0, duration: 0.4, ease: "back.out(1.2)", onComplete: () => {
                gsap.set(sheet, { clearProps: "all" });
            }});
        }
        currentY = 0;
    }

    handleArea.addEventListener('touchstart', onDragStart, { passive: true });
    handleArea.addEventListener('touchmove', onDragMove, { passive: true });
    handleArea.addEventListener('touchend', onDragEnd);
    handleArea.addEventListener('mousedown', onDragStart);
    window.addEventListener('mousemove', onDragMove);
    window.addEventListener('mouseup', onDragEnd);
}

function initKeyboardHandling() {
    document.querySelectorAll('.bottom-sheet').forEach(sheet => {
        sheet.addEventListener('click', (e) => {
            if (e.target === sheet || e.target.classList.contains('checkout-header') || e.target.classList.contains('cart-header')) {
                if (document.activeElement && document.activeElement.tagName === 'INPUT') {
                    document.activeElement.blur(); 
                }
            }
        });
    });

    document.querySelectorAll('#checkout-screen input, #checkout-screen textarea').forEach(input => {
        input.addEventListener('focus', (e) => {
            if (tg?.HapticFeedback) tg.HapticFeedback.selectionChanged();
            const sheet = document.getElementById('checkout-screen');
            sheet.style.paddingBottom = '350px';
            setTimeout(() => {
                e.target.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }, 250);
        });
        
        input.addEventListener('blur', () => {
            const sheet = document.getElementById('checkout-screen');
            sheet.style.paddingBottom = '20px'; 
        });
    });
}

function initEnterNavigation() {
    const inputIds = ['username', 'phone', 'street', 'house', 'entrance', 'floor', 'flat', 'comment'];
    
    inputIds.forEach((id, index) => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    if (index < inputIds.length - 1) {
                        document.getElementById(inputIds[index + 1]).focus();
                    } else {
                        el.blur();
                    }
                }
            });
        }
    });
}

function initPhoneMask() {
    const phoneInput = document.getElementById('phone');
    if (!phoneInput) return;

    phoneInput.addEventListener('input', function (e) {
        let input = e.target.value.replace(/\D/g, ''); 
        if (!input) { e.target.value = ''; return; }
        
        if (['7', '8', '9'].includes(input[0])) {
            if (input[0] === '9') input = '7' + input;
            let formatted = '+7 ';
            if (input.length > 1) formatted += '(' + input.substring(1, 4);
            if (input.length >= 5) formatted += ') ' + input.substring(4, 7);
            if (input.length >= 8) formatted += '-' + input.substring(7, 9);
            if (input.length >= 10) formatted += '-' + input.substring(9, 11);
            e.target.value = formatted;
        } else {
            e.target.value = '+' + input.substring(0, 15);
        }

        if (e.target.value.length === 18) {
            e.target.blur();
        }
    });

    phoneInput.addEventListener('keydown', function(e) {
        if (e.key === 'Backspace' && e.target.value.length <= 4) e.target.value = '';
    });
    phoneInput.addEventListener('focus', function(e) {
         if (!e.target.value) e.target.value = '+7 ';
    });
    phoneInput.addEventListener('blur', function(e) {
         if (e.target.value === '+7 ' || e.target.value === '+7') e.target.value = '';
    });
}

// ================= ЦЕНТРИРОВАННЫЙ iOS POP-UP БАРАБАН =================
function initPickerData() {
    const months = ['янв', 'фев', 'мар', 'апр', 'мая', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];
    let d = new Date();
    let currentDay = d.getDay();
    let daysToSat = (6 - currentDay + 7) % 7;
    let firstSat = new Date(d);
    firstSat.setDate(d.getDate() + daysToSat);

    for (let i = 0; i < 4; i++) {
        let sat = new Date(firstSat);
        sat.setDate(firstSat.getDate() + (i * 7));
        saturdaysData.push({
            value: sat.toISOString(),
            label: `Суббота, ${sat.getDate()} ${months[sat.getMonth()]}`,
            isToday: daysToSat === 0 && i === 0
        });
    }

    populateWheel('wheel-date', saturdaysData);
    updateHoursWheel(0);
    
    let minutes = [];
    for (let i = 0; i <= 55; i += 5) {
        minutes.push({ value: i.toString().padStart(2, '0'), label: i.toString().padStart(2, '0') });
    }
    populateWheel('wheel-minutes', minutes);
    
    initPickerScroll();
}

function updateHoursWheel(dateIndex) {
    let isToday = saturdaysData[dateIndex]?.isToday;
    let currentHour = new Date().getHours();
    let startHour = (isToday && currentHour >= 10) ? Math.max(10, currentHour + 1) : 10;
    
    let hours = [];
    if (startHour <= 20) {
        for (let i = startHour; i <= 20; i++) {
            hours.push({ value: i.toString().padStart(2, '0'), label: i.toString().padStart(2, '0') });
        }
    } else {
        hours.push({ value: '-', label: '-' });
    }
    populateWheel('wheel-hours', hours);
}

function populateWheel(wheelId, items) {
    const wheel = document.getElementById(wheelId);
    wheel.innerHTML = '';
    items.forEach((item, index) => {
        let div = document.createElement('div');
        div.className = `picker-item ${index === 0 ? 'active' : ''}`;
        div.dataset.value = item.value;
        div.innerText = item.label;
        wheel.appendChild(div);
    });
    wheel.scrollTop = 0;
    wheel.dataset.lastIndex = 0;
}

function initPickerScroll() {
    ['wheel-date', 'wheel-hours', 'wheel-minutes'].forEach(id => {
        const wheel = document.getElementById(id);
        let scrollTimeout;

        wheel.addEventListener('scroll', () => {
            let index = Math.round(wheel.scrollTop / 44);
            let maxIndex = wheel.children.length - 1;
            index = Math.max(0, Math.min(index, maxIndex));

            if (index !== parseInt(wheel.dataset.lastIndex || 0)) {
                wheel.dataset.lastIndex = index;
                if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('light');

                Array.from(wheel.children).forEach((child, i) => {
                    child.classList.toggle('active', i === index);
                });

                if (id === 'wheel-date') {
                    updateHoursWheel(index);
                }
            }

            // ЖЕСТКИЙ АВТОДОВОДЧИК БЕЗ НЕДОКРУТОВ
            window.clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                const itemHeight = 44;
                const targetIndex = Math.round(wheel.scrollTop / itemHeight);
                wheel.scrollTo({ top: targetIndex * itemHeight, behavior: 'smooth' });
            }, 100);
        });
    });
}

function openPicker() {
    if (document.activeElement && document.activeElement.tagName === 'INPUT') {
        document.activeElement.blur(); 
    }

    if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('light');
    
    document.getElementById('picker-overlay').classList.add('active');
    document.getElementById('picker-modal').classList.add('active');

    gsap.to('#picker-overlay', { opacity: 1, duration: 0.3 });
    gsap.fromTo('#picker-modal',
        { xPercent: -50, yPercent: -50, scale: 0.85, opacity: 0, top: '50%', left: '50%' },
        { scale: 1, opacity: 1, duration: 0.4, ease: "back.out(1.5)" }
    );
}

function closePickerAndSave() {
    if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
    
    let dateWheel = document.getElementById('wheel-date');
    let hoursWheel = document.getElementById('wheel-hours');
    let minsWheel = document.getElementById('wheel-minutes');

    let dIdx = parseInt(dateWheel.dataset.lastIndex || 0);
    let hIdx = parseInt(hoursWheel.dataset.lastIndex || 0);
    let mIdx = parseInt(minsWheel.dataset.lastIndex || 0);

    let dateStr = dateWheel.children[dIdx]?.innerText || '';
    let hourStr = hoursWheel.children[hIdx]?.innerText || '';
    let minStr = minsWheel.children[mIdx]?.innerText || '';

    const valEl = document.getElementById('delivery-time-value');

    if (hourStr === '-') {
        valEl.innerText = 'Нет доступного времени';
        valEl.classList.remove('placeholder');
    } else {
        valEl.innerText = `${dateStr} в ${hourStr}:${minStr}`;
        valEl.classList.remove('placeholder');
    }
    
    gsap.to('#picker-overlay', { opacity: 0, duration: 0.3, onComplete: () => {
        document.getElementById('picker-overlay').classList.remove('active');
    }});
    gsap.to('#picker-modal', { scale: 0.8, opacity: 0, duration: 0.3, ease: "power2.in", onComplete: () => {
        document.getElementById('picker-modal').classList.remove('active');
    }});
}

function initAnimations() {
    const titleEl = document.querySelector('.header .brand-title');
    if(!titleEl) return;
    const text = titleEl.innerText;
    titleEl.innerHTML = '';

    text.split('').forEach(char => {
        const span = document.createElement('span');
        span.innerText = char;
        span.style.display = 'inline-block';
        span.style.opacity = '0';
        span.style.filter = 'blur(12px)';
        span.style.transform = 'scale(0.8)';
        titleEl.appendChild(span);
    });

    const tl = gsap.timeline();
    tl.to(".header .brand-title span", {
        duration: 0.9, opacity: 1, filter: "blur(0px)", scale: 1, ease: "power2.out", stagger: 0.06, delay: 0.1
    }).to("#sweet-subtitle", { duration: 0.8, opacity: 1, ease: "power2.out" }, "-=0.3");
}

// Инициализация
initTelegramData();
initPickerData();
renderProducts();
initAnimations();
initPhoneMask();
initBottomSheetSwipe('cart-screen', 'drag-handle-cart');
initBottomSheetSwipe('checkout-screen', 'drag-handle-checkout');
initKeyboardHandling();
initEnterNavigation();