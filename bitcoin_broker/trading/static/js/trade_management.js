// Trade Management JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize trade management
    initializeTradingUI();
    loadActiveTrades();
    loadTradeHistory();
    setupTradeForm();
    setupOrderForm();
    
    // Start real-time updates
    setInterval(updateActiveTrades, 5000); // Update every 5 seconds
    setInterval(updatePrices, 2000); // Update prices every 2 seconds
});

function initializeTradingUI() {
    // Setup trade type dependent fields
    const orderTypeSelect = document.getElementById('order-type');
    if (orderTypeSelect) {
        orderTypeSelect.addEventListener('change', function() {
            const priceInput = document.getElementById('price-input');
            const stopPriceInput = document.getElementById('stop-price-input');
            const trailingInput = document.getElementById('trailing-percent-input');
            
            // Hide all price fields first
            [priceInput, stopPriceInput, trailingInput].forEach(el => el.classList.add('hidden'));
            
            // Show relevant fields based on order type
            switch(this.value) {
                case 'limit':
                    priceInput.classList.remove('hidden');
                    break;
                case 'stop_loss':
                case 'stop_limit':
                    stopPriceInput.classList.remove('hidden');
                    if (this.value === 'stop_limit') priceInput.classList.remove('hidden');
                    break;
                case 'trailing_stop':
                    trailingInput.classList.remove('hidden');
                    break;
            }
        });
    }

    // Setup buy/sell toggle
    const buyBtn = document.getElementById('buy-btn');
    const sellBtn = document.getElementById('sell-btn');
    
    if (buyBtn && sellBtn) {
        buyBtn.addEventListener('click', () => {
            buyBtn.classList.remove('bg-gray-200', 'text-gray-700');
            buyBtn.classList.add('bg-green-600', 'text-white');
            sellBtn.classList.remove('bg-red-600', 'text-white');
            sellBtn.classList.add('bg-gray-200', 'text-gray-700');
        });
        
        sellBtn.addEventListener('click', () => {
            sellBtn.classList.remove('bg-gray-200', 'text-gray-700');
            sellBtn.classList.add('bg-red-600', 'text-white');
            buyBtn.classList.remove('bg-green-600', 'text-white');
            buyBtn.classList.add('bg-gray-200', 'text-gray-700');
        });
    }

    // Load available assets
    loadAvailableAssets();
}

async function loadAvailableAssets() {
    try {
        const response = await fetch('/api/assets/');
        const assets = await response.json();
        
        const assetSelect = document.getElementById('asset-symbol');
        assets.forEach(asset => {
            const option = document.createElement('option');
            option.value = asset.symbol;
            option.textContent = `${asset.name} (${asset.symbol})`;
            assetSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading assets:', error);
        showNotification('Error loading assets', 'error');
    }
}

async function loadActiveTrades() {
    try {
        const response = await fetch('/api/trades/active/');
        const trades = await response.json();
        
        const tableBody = document.getElementById('active-trades');
        tableBody.innerHTML = ''; // Clear existing trades
        
        trades.forEach(trade => {
            const row = createTradeRow(trade);
            tableBody.appendChild(row);
        });
    } catch (error) {
        console.error('Error loading active trades:', error);
        showNotification('Error loading active trades', 'error');
    }
}

async function loadTradeHistory() {
    try {
        const response = await fetch('/api/trades/history/');
        const trades = await response.json();
        
        const tableBody = document.getElementById('trade-history');
        tableBody.innerHTML = ''; // Clear existing history
        
        trades.forEach(trade => {
            const row = createHistoryRow(trade);
            tableBody.appendChild(row);
        });
    } catch (error) {
        console.error('Error loading trade history:', error);
        showNotification('Error loading trade history', 'error');
    }
}

function createTradeRow(trade) {
    const row = document.createElement('tr');
    row.className = 'hover:bg-gray-800 transition-colors';
    
    // Calculate P/L
    const pl = trade.profit_loss;
    const plClass = pl >= 0 ? 'text-green-500' : 'text-red-500';
    
    row.innerHTML = `
        <td class="px-6 py-4 whitespace-nowrap text-primary">${trade.asset.symbol}</td>
        <td class="px-6 py-4 whitespace-nowrap text-primary">${formatTradeType(trade.trade_type)}</td>
        <td class="px-6 py-4 whitespace-nowrap text-primary">
            <span class="${trade.side === 'buy' ? 'text-green-500' : 'text-red-500'}">${trade.side.toUpperCase()}</span>
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-primary">${formatPrice(trade.entry_price)}</td>
        <td class="px-6 py-4 whitespace-nowrap text-primary">${formatPrice(trade.current_price)}</td>
        <td class="px-6 py-4 whitespace-nowrap ${plClass}">${formatPrice(pl)} (${trade.profit_loss_percentage}%)</td>
        <td class="px-6 py-4 whitespace-nowrap">
            <div class="flex space-x-2">
                <button onclick="closeTrade(${trade.id})" class="text-white bg-red-600 hover:bg-red-700 font-medium rounded-lg text-sm px-3 py-1.5 transition-colors">Close</button>
                <button onclick="editTrade(${trade.id})" class="text-white bg-indigo-600 hover:bg-indigo-700 font-medium rounded-lg text-sm px-3 py-1.5 transition-colors">Edit</button>
            </div>
        </td>
    `;
    
    return row;
}

function createHistoryRow(trade) {
    const row = document.createElement('tr');
    row.className = 'hover:bg-gray-800 transition-colors';
    
    const pl = trade.profit_loss;
    const plClass = pl >= 0 ? 'text-green-500' : 'text-red-500';
    const statusClass = getStatusClass(trade.status);
    
    row.innerHTML = `
        <td class="px-6 py-4 whitespace-nowrap text-primary">${formatDate(trade.created_at)}</td>
        <td class="px-6 py-4 whitespace-nowrap text-primary">${trade.asset.symbol}</td>
        <td class="px-6 py-4 whitespace-nowrap text-primary">${formatTradeType(trade.trade_type)}</td>
        <td class="px-6 py-4 whitespace-nowrap">
            <span class="${trade.side === 'buy' ? 'text-green-500' : 'text-red-500'}">${trade.side.toUpperCase()}</span>
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-primary">${formatPrice(trade.entry_price)} → ${formatPrice(trade.exit_price)}</td>
        <td class="px-6 py-4 whitespace-nowrap ${plClass}">${formatPrice(pl)} (${trade.profit_loss_percentage}%)</td>
        <td class="px-6 py-4 whitespace-nowrap">
            <span class="px-2 py-1 text-xs font-medium rounded-full ${statusClass}">${trade.status}</span>
        </td>
    `;
    
    return row;
}

function setupOrderForm() {
    const form = document.getElementById('order-form');
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(form);
            const orderData = {
                asset_symbol: document.getElementById('asset-symbol').value,
                order_type: document.getElementById('order-type').value,
                side: document.getElementById('buy-btn').classList.contains('bg-green-600') ? 'buy' : 'sell',
                quantity: document.getElementById('quantity').value,
                price: document.getElementById('price')?.value,
                stop_price: document.getElementById('stop-price')?.value,
                trailing_percent: document.getElementById('trailing-percent')?.value
            };
            
            try {
                const response = await fetch('/api/trades/create/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify(orderData)
                });
                
                if (response.ok) {
                    showNotification('Order placed successfully', 'success');
                    form.reset();
                    loadActiveTrades(); // Refresh active trades
                } else {
                    const error = await response.json();
                    showNotification(error.message || 'Error placing order', 'error');
                }
            } catch (error) {
                console.error('Error placing order:', error);
                showNotification('Error placing order', 'error');
            }
        });
    }
}

async function closeTrade(tradeId) {
    if (!confirm('Are you sure you want to close this trade?')) return;
    
    try {
        const response = await fetch(`/api/trades/${tradeId}/close/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        if (response.ok) {
            showNotification('Trade closed successfully', 'success');
            loadActiveTrades(); // Refresh active trades
            loadTradeHistory(); // Refresh trade history
        } else {
            const error = await response.json();
            showNotification(error.message || 'Error closing trade', 'error');
        }
    } catch (error) {
        console.error('Error closing trade:', error);
        showNotification('Error closing trade', 'error');
    }
}

async function editTrade(tradeId) {
    // Implementation for editing trade (e.g., updating stop loss, take profit)
    // This would typically open a modal with the trade details
    showNotification('Trade editing coming soon', 'info');
}

async function updateActiveTrades() {
    await loadActiveTrades();
}

async function updatePrices() {
    try {
        const response = await fetch('/api/market/prices/');
        const prices = await response.json();
        
        // Update current price display
        document.getElementById('current-price').textContent = formatPrice(prices.current);
        
        // Update price change
        const priceChange = document.getElementById('price-change');
        const changePercent = prices.change_24h;
        priceChange.textContent = `${changePercent > 0 ? '+' : ''}${changePercent.toFixed(2)}%`;
        priceChange.className = `text-sm ${changePercent >= 0 ? 'text-green-500' : 'text-red-500'}`;
        
        // Update technical indicators
        document.getElementById('rsi-value').textContent = prices.rsi.toFixed(2);
        document.getElementById('macd-value').textContent = prices.macd.toFixed(2);
        document.getElementById('volume-value').textContent = formatVolume(prices.volume_24h);
        document.getElementById('high-low-value').textContent = `${formatPrice(prices.high_24h)}/${formatPrice(prices.low_24h)}`;
    } catch (error) {
        console.error('Error updating prices:', error);
    }
}

// Utility functions
function formatPrice(price) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 8
    }).format(price);
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatVolume(volume) {
    if (volume >= 1e9) return `${(volume / 1e9).toFixed(2)}B`;
    if (volume >= 1e6) return `${(volume / 1e6).toFixed(2)}M`;
    if (volume >= 1e3) return `${(volume / 1e3).toFixed(2)}K`;
    return volume.toFixed(2);
}

function formatTradeType(type) {
    return type.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
}

function getStatusClass(status) {
    switch (status.toLowerCase()) {
        case 'completed':
            return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
        case 'cancelled':
            return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
        case 'pending':
            return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300';
        default:
            return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300';
    }
}

function showNotification(message, type = 'info') {
    // You can implement this using your preferred notification library
    // For example: toastr, sweetalert2, or a custom implementation
    console.log(`${type.toUpperCase()}: ${message}`);
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
