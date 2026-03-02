---
title: E-Commerce Shopping Cart
author: Product Team
priority: high
---

# Shopping Cart User Stories

## Cart Management

### Add to Cart

As a customer, I want to add products to my cart so that I can purchase
multiple items at once.

Acceptance Criteria:
- Clicking "Add to Cart" adds the item with quantity 1
- If the item is already in the cart, increment the quantity
- Show a toast notification confirming the item was added
- Update the cart badge count in the header
- Cart persists across page refreshes (localStorage + server sync)

### Update Quantity

As a customer, I want to change the quantity of items in my cart so that
I can buy more or fewer of each product.

Acceptance Criteria:
- Quantity selector allows values from 1 to max stock
- Updating quantity recalculates line item total and cart total
- Setting quantity to 0 removes the item (with confirmation)

### Remove Item

As a customer, I want to remove items from my cart so that I only
purchase what I need.

Acceptance Criteria:
- Each cart item has a "Remove" button
- Removing an item shows an "Undo" option for 5 seconds
- Cart total updates immediately

## Checkout Flow

### Cart Summary

As a customer, I want to see a summary of my cart before checkout so
that I can verify my order.

Acceptance Criteria:
- Shows each item with: name, image thumbnail, unit price, quantity, line total
- Shows subtotal, tax estimate, shipping estimate, and grand total
- Shows estimated delivery date
- "Proceed to Checkout" button is disabled if cart is empty

### Apply Coupon

As a customer, I want to apply discount coupons so that I can save money.

Acceptance Criteria:
- Single text input for coupon code
- Validates code against backend on submit
- Shows discount amount and updated total
- Only one coupon per order
- Clear error message for invalid/expired coupons
