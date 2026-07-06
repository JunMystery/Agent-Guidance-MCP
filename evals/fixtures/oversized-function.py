def process_order(order):
    # Validate
    if not order.get("items"):
        return None

    # Calculate totals
    subtotal = sum(item["price"] * item["qty"] for item in order["items"])
    tax = subtotal * 0.08
    shipping = 10 if subtotal < 50 else 0

    # Apply discount
    if order.get("coupon"):
        if order["coupon"] == "WELCOME10":
            subtotal *= 0.9
        elif order["coupon"] == "VIP20":
            subtotal *= 0.8

    # Save to database
    db.orders.insert({
        "items": order["items"],
        "subtotal": subtotal,
        "tax": tax,
        "shipping": shipping,
        "total": subtotal + tax + shipping,
        "timestamp": datetime.now()
    })

    # Send confirmation
    email.send(order["email"], "Order Confirmed", f"Total: ${subtotal + tax + shipping}")

    # Update inventory
    for item in order["items"]:
        db.inventory.update(
            {"sku": item["sku"]},
            {"$inc": {"stock": -item["qty"]}}
        )

    # Log
    logger.info(f"Order processed: {order['id']}")

    return {"status": "ok", "order_id": order["id"]}
