odoo.define('altanmia_event_venue.collapse_tickets', function (require) {
    $(document).ready(function () {
        $('.toggle-group-collapse').on('click', function (e) {
            e.preventDefault();
            var group = $(this).data('group');
            var sanitizedGroup = group.replace(/ /g, '_');
            var ticketGroupId = 'group-' + sanitizedGroup;
            var ticketGroup = $('#' + ticketGroupId);
            if (ticketGroup.length > 0) {
                ticketGroup.toggle();
                if (ticketGroup.is(':visible')) {
                    $(this).text(' Hide');
                } else {
                    $(this).text(' Show');
                }
            } else {
                console.error('Element not found for ID:', ticketGroupId);
            }
        });
    });

    $(document).ready(function () {
        $('.toggle-tickets').on('click', function (e) {
            e.preventDefault();
            var group = $(this).data('group');
            var sanitizedGroup = group;
            var ticketGroupId = 'group-' + sanitizedGroup;
            var ticketGroup = $('#' + ticketGroupId);
            if (ticketGroup.length > 0) {
                ticketGroup.toggle();
                if (ticketGroup.is(':visible')) {
                    $(this).text(' Hide');
                } else {
                    $(this).text(' Show');
                }
            } else {
                console.error('Element not found for ID:', ticketGroupId);
            }
        });
    });

    document.addEventListener("input", function (event) {
        const inputs = document.querySelectorAll('.ticket-num');
        let totalTickets = 0;
        if (event.target.classList.contains("ticket-num")) {
            const input = event.target;
            const maxQty = parseInt(input.getAttribute("data-max-qty")) || Infinity;
            const productQtyElement = event.target.closest(".product_uom").querySelector(".product-qty");
            if (!productQtyElement) {
                console.error("Product quantity element not found!");
                return;
            }
            let productQty = parseInt(productQtyElement.getAttribute("data-product-qty")) || 0;
            let currentValue = parseInt(input.value) || 0;
            let previousValue = parseInt(input.getAttribute("data-prev-value")) || 0;
            if (currentValue < 0) {
                input.value = 0;
                currentValue = 0;
            }
            if (currentValue > maxQty) {
                alert(`You cannot select more than ${maxQty} items.`);
                input.value = previousValue;
                currentValue = previousValue;
            }
            const difference = currentValue - previousValue;
            if (productQty - difference >= 0) {
                productQty -= difference;
                productQtyElement.setAttribute("data-product-qty", productQty);
                productQtyElement.textContent = productQty;
            } else {
                alert("Not enough quantity available.");
                input.value = previousValue;
                currentValue = previousValue;
            }
            input.setAttribute("data-prev-value", currentValue);
        }
        inputs.forEach(input => {
            totalTickets += parseInt(input.value) || 0;
        });
        const ticketCountElement = document.getElementById('ticketCount');
        if (ticketCountElement) {
            ticketCountElement.textContent = `${totalTickets} tickets selected`;
        } else {
            console.error("Element with id 'ticketCount' not found.");
        }
    });

    document.addEventListener("click", function (event) {
        const inputs = document.querySelectorAll('.ticket-num');
        let totalTickets = 0;
        if (event.target.classList.contains("increment-btn")) {
            const input = event.target.previousElementSibling;
            const maxQty = parseInt(input.getAttribute("data-max-qty")) || Infinity;
            let currentValue = parseInt(input.value) || 0;
            if (currentValue < maxQty) {
                const productQtyElement = event.target.closest(".product_uom").querySelector(".product-qty");
                if (productQtyElement) {
                    let productQty = parseInt(productQtyElement.getAttribute("data-product-qty")) || 0;

                    if (productQty > 0) {
                        input.value = currentValue + 1;
                        currentValue++;
                        productQtyElement.setAttribute("data-product-qty", productQty - 1);
                        productQtyElement.textContent = productQty - 1;
                    } else {
                        alert("No more quantity available.");
                    }
                } else {
                    console.error("Product quantity element not found!");
                }
            } else {
                alert("You cannot select more than the available quantity.");
            }
            input.setAttribute("data-prev-value", currentValue);
        }
        if (event.target.classList.contains("decrement-btn")) {
            const input = event.target.nextElementSibling;
            let currentValue = parseInt(input.value) || 0;
            if (currentValue > 0) {
                const productQtyElement = event.target.closest(".product_uom").querySelector(".product-qty");
                if (productQtyElement) {
                    let productQty = parseInt(productQtyElement.getAttribute("data-product-qty")) || 0;
                    input.value = currentValue - 1;
                    currentValue--;
                    productQtyElement.setAttribute("data-product-qty", productQty + 1);
                    productQtyElement.textContent = productQty + 1;
                } else {
                    console.error("Product quantity element not found!");
                }
            }
            input.setAttribute("data-prev-value", currentValue);
        }
        inputs.forEach(input => {
            totalTickets += parseInt(input.value) || 0;
        });
        const ticketCountElement = document.getElementById('ticketCount');
        if (ticketCountElement) {
            ticketCountElement.textContent = `${totalTickets} tickets selected`;
        } else {
            console.error("Element with id 'ticketCount' not found.");
        }
    });

});