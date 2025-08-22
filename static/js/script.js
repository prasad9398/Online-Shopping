document.addEventListener('DOMContentLoaded', function() {
    const quantitySelect = document.getElementById('quantity');
    const hiddenQuantity = document.getElementById('hidden-quantity');

    if (quantitySelect && hiddenQuantity) {
        quantitySelect.addEventListener('change', function() {
            hiddenQuantity.value = this.value;
        });
    }
});

document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth'
            });
        }
    });
});