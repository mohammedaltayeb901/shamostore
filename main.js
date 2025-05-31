// Custom JavaScript for Game Shipping Site

$(document).ready(function() {
    // Function to update the cart count in the navbar
    function updateCartCount() {
        $.ajax({
            url: "/api/cart", // Use the API endpoint to get cart data
            type: "GET",
            success: function(response) {
                if (response.success && response.data && response.data.items) {
                    let itemCount = 0;
                    response.data.items.forEach(item => {
                        itemCount += item.quantity;
                    });
                    $("#cart-count").text(itemCount);
                } else {
                    $("#cart-count").text(0);
                }
            },
            error: function() {
                // Handle error, maybe show 0 or a placeholder
                $("#cart-count").text("?"); 
                console.error("Failed to fetch cart count.");
            }
        });
    }

    // Update cart count on page load
    updateCartCount();

    // Expose the updateCartCount function globally if needed by other scripts
    window.updateCartCount = updateCartCount;

    // Example: Add to cart button functionality (can be refined)
    // This might be better placed within specific page templates or a dedicated cart script
    $(document).on("click", ".add-to-cart-btn", function() {
        const gameId = $(this).data("game-id");
        const quantity = 1; // Or get from an input field
        const gameAccountId = $(`#game-account-id-${gameId}`).val(); // Example if account ID is needed

        $.ajax({
            url: "/api/cart/add",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({ 
                game_id: gameId, 
                quantity: quantity,
                game_account_id: gameAccountId // Include if applicable
            }),
            success: function(response) {
                if (response.success) {
                    // Optionally show a success message (e.g., using a toast notification)
                    alert(response.message); // Simple alert for now
                    updateCartCount(); // Update count in navbar
                } else {
                    alert("Error: " + response.message);
                }
            },
            error: function(xhr) {
                let errorMsg = "حدث خطأ أثناء إضافة المنتج للسلة.";
                if (xhr.responseJSON && xhr.responseJSON.message) {
                    errorMsg = xhr.responseJSON.message;
                }
                alert("Error: " + errorMsg);
                console.error("Failed to add item to cart.");
            }
        });
    });

});
