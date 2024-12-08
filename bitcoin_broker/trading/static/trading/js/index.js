// Auto-update crypto prices every minute
function updateCryptoPrices() {
    fetch('/api/prices/')
        .then(response => response.json())
        .then(data => {
            Object.entries(data).forEach(([symbol, priceData]) => {
                // Update price
                const priceElement = document.querySelector(`[data-symbol="${symbol}"] .price`);
                if (priceElement) {
                    priceElement.textContent = `$${parseFloat(priceData.price).toFixed(2)}`;
                }
                
                // Update change percentage
                const changeElement = document.querySelector(`[data-symbol="${symbol}"] .change`);
                if (changeElement) {
                    const change = parseFloat(priceData.change_24h);
                    changeElement.textContent = `${change.toFixed(2)}%`;
                    changeElement.className = `change ${change >= 0 ? 'positive' : 'negative'}`;
                }
                
                // Update other details
                const volumeElement = document.querySelector(`[data-symbol="${symbol}"] .volume`);
                if (volumeElement) {
                    volumeElement.textContent = `24h Volume: $${parseInt(priceData.volume).toLocaleString()}`;
                }
                
                const highElement = document.querySelector(`[data-symbol="${symbol}"] .high`);
                if (highElement) {
                    highElement.textContent = `24h High: $${parseFloat(priceData.high_24h).toFixed(2)}`;
                }
                
                const lowElement = document.querySelector(`[data-symbol="${symbol}"] .low`);
                if (lowElement) {
                    lowElement.textContent = `24h Low: $${parseFloat(priceData.low_24h).toFixed(2)}`;
                }
            });
        })
        .catch(error => console.error('Error updating prices:', error));
}

// Update prices every minute
setInterval(updateCryptoPrices, 60000);

// Add smooth scrolling for navigation links
document.addEventListener('DOMContentLoaded', function() {
    const links = document.querySelectorAll('a[href^="#"]');
    
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});
