
import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
PRODUCTS_FILE = BASE_DIR / "products.json"

# Load synthetic products
with open(PRODUCTS_FILE, "r", encoding="utf-8") as file:
    products = json.load(file)

# Temporary shopping cart
cart = []


@app.route("/")
def home():
    return render_template("shop.html")


@app.route("/api/products")
def get_products():
    filtered = products.copy()

    search = request.args.get("search", "").lower()
    color = request.args.get("color", "").lower()
    size = request.args.get("size", "")
    max_price = request.args.get("max_price", "")
    sort = request.args.get("sort", "")

    if search:
        filtered = [
            p for p in filtered
            if search in p["name"].lower()
            or search in p["brand"].lower()
        ]

    if color:
        filtered = [
            p for p in filtered
            if p["color"].lower() == color
        ]

    if size:
        filtered = [
            p for p in filtered
            if p["size"] == int(size)
        ]

    if max_price:
        filtered = [
            p for p in filtered
            if p["price"] <= float(max_price)
        ]

    if sort == "price_low":
        filtered.sort(key=lambda p: p["price"])

    elif sort == "price_high":
        filtered.sort(key=lambda p: p["price"], reverse=True)

    return jsonify(filtered)


@app.route("/api/cart", methods=["GET"])
def get_cart():
    return jsonify(cart)


@app.route("/api/cart/add", methods=["POST"])
def add_to_cart():
    data = request.get_json()
    product_id = data.get("product_id")

    product = next(
        (p for p in products if p["id"] == product_id),
        None
    )

    if product is None:
        return jsonify({"error": "Product not found"}), 404

    if any(item["id"] == product_id for item in cart):
        return jsonify({"message": "Product already in cart"})

    cart.append(product)

    return jsonify({
        "message": "Product added to cart",
        "cart": cart
    })


@app.route("/api/cart/remove", methods=["POST"])
def remove_from_cart():
    data = request.get_json()
    product_id = data.get("product_id")

    cart[:] = [
        item for item in cart
        if item["id"] != product_id
    ]

    return jsonify({"message": "Product removed", "cart": cart})


@app.route("/api/cart/clear", methods=["POST"])
def clear_cart():
    cart.clear()
    return jsonify({"message": "Cart cleared"})


if __name__ == "__main__":
    app.run(port=5001, debug=True, use_reloader=False)
