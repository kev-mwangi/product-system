from flask import Flask, jsonify, request
from flask_cors import CORS
import requests as http_requests
 
app = Flask(__name__)
CORS(app)
 
 
# ---------------------------------------------------------------------------
# Item model
# ---------------------------------------------------------------------------
 
class Item:
    def __init__(self, id, name, barcode, quantity, price, category="General"):
        self.id = id
        self.name = name
        self.barcode = barcode
        self.quantity = quantity
        self.price = price
        self.category = category
 
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "barcode": self.barcode,
            "quantity": self.quantity,
            "price": self.price,
            "category": self.category,
        }
 
 
# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------
 
inventory = [
    Item(1, "Coca-Cola 500ml", "5449000000996", 50, 1.99, "Beverages"),
    Item(2, "Lays Classic Chips", "0028400315012", 30, 2.49, "Snacks"),
    Item(3, "Minute Maid Orange", "0025000056954", 20, 1.79, "Beverages"),
]
 
next_id = 4
 
 
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
 
def find_item(item_id):
    """Return Item by id or None."""
    return next((i for i in inventory if i.id == item_id), None)
 
 
# OpenFoodFacts asks apps to identify themselves with a custom User-Agent
# rather than the requests library default.
OFF_HEADERS = {
    "User-Agent": "InventorySystem/1.0 (youremail@example.com)"
}
 
 
def fetch_openfoodfacts(barcode):
    """
    Call OpenFoodFacts API for a given barcode.
    Returns a dict with product info, or None if not found. Raises
    requests.exceptions.RequestException on network/HTTP failures.
    """
    # v3 is the current recommended product-lookup endpoint (v0 is long
    # deprecated and may be removed).
    url = f"https://world.openfoodfacts.org/api/v3/product/{barcode}.json"
    response = http_requests.get(url, headers=OFF_HEADERS, timeout=5)
    response.raise_for_status()
    data = response.json()
 
    if data.get("status") != 1:
        return None  # product not found
 
    product = data["product"]
    return {
        "name": product.get("product_name", "Unknown"),
        "barcode": barcode,
        "category": product.get("categories_tags", ["General"])[0]
                    .replace("en:", "").replace("-", " ").title()
                    if product.get("categories_tags") else "General",
        "image_url": product.get("image_url", ""),
        "brands": product.get("brands", ""),
        "quantity_info": product.get("quantity", ""),
    }
 
 
# ---------------------------------------------------------------------------
# CRUD Routes
# ---------------------------------------------------------------------------
 
# GET /inventory — list all items
@app.route("/inventory", methods=["GET"])
def get_inventory():
    return jsonify([i.to_dict() for i in inventory]), 200
 
 
# GET /inventory/<id> — get a single item
@app.route("/inventory/<int:item_id>", methods=["GET"])
def get_item(item_id):
    item = find_item(item_id)
    if item is None:
        return jsonify({"error": f"Item with id {item_id} not found."}), 404
    return jsonify(item.to_dict()), 200
 
 
# POST /inventory — create a new item
@app.route("/inventory", methods=["POST"])
def create_item():
    global next_id
    data = request.get_json(silent=True)
 
    # Validate required fields
    required = ["name", "barcode", "quantity", "price"]
    missing = [f for f in required if not data or f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {missing}"}), 400
 
    # Validate types
    try:
        quantity = int(data["quantity"])
        price = float(data["price"])
    except (ValueError, TypeError):
        return jsonify({"error": "'quantity' must be int and 'price' must be a number."}), 400
 
    item = Item(
        id=next_id,
        name=str(data["name"]).strip(),
        barcode=str(data["barcode"]).strip(),
        quantity=quantity,
        price=price,
        category=str(data.get("category", "General")).strip(),
    )
    inventory.append(item)
    next_id += 1
 
    return jsonify(item.to_dict()), 201
 
 
# PATCH /inventory/<id> — partial update
@app.route("/inventory/<int:item_id>", methods=["PATCH"])
def update_item(item_id):
    item = find_item(item_id)
    if item is None:
        return jsonify({"error": f"Item with id {item_id} not found."}), 404
 
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400
 
    # Apply only the fields that were sent
    if "name" in data:
        item.name = str(data["name"]).strip()
    if "barcode" in data:
        item.barcode = str(data["barcode"]).strip()
    if "quantity" in data:
        try:
            item.quantity = int(data["quantity"])
        except (ValueError, TypeError):
            return jsonify({"error": "'quantity' must be an integer."}), 400
    if "price" in data:
        try:
            item.price = float(data["price"])
        except (ValueError, TypeError):
            return jsonify({"error": "'price' must be a number."}), 400
    if "category" in data:
        item.category = str(data["category"]).strip()
 
    return jsonify(item.to_dict()), 200
 
 
# DELETE /inventory/<id> — remove item
@app.route("/inventory/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    item = find_item(item_id)
    if item is None:
        return jsonify({"error": f"Item with id {item_id} not found."}), 404
 
    inventory.remove(item)
    return "", 204
 
 
# ---------------------------------------------------------------------------
# External API Routes
# ---------------------------------------------------------------------------
 
# GET /lookup/<barcode> — fetch product info from OpenFoodFacts
@app.route("/lookup/<barcode>", methods=["GET"])
def lookup_barcode(barcode):
    try:
        product = fetch_openfoodfacts(barcode)
    except http_requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to reach OpenFoodFacts: {str(e)}"}), 502
 
    if product is None:
        return jsonify({"error": f"No product found for barcode {barcode}."}), 404
 
    return jsonify(product), 200
 
 
# POST /lookup/<barcode>/import — look up a barcode and add it to inventory
@app.route("/lookup/<barcode>/import", methods=["POST"])
def import_from_barcode(barcode):
    global next_id
 
    # Optional overrides in body
    overrides = request.get_json(silent=True) or {}
 
    try:
        product = fetch_openfoodfacts(barcode)
    except http_requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to reach OpenFoodFacts: {str(e)}"}), 502
 
    if product is None:
        return jsonify({"error": f"No product found for barcode {barcode}."}), 404
 
    # Build the item, letting the caller override quantity/price
    item = Item(
        id=next_id,
        name=overrides.get("name", product["name"]) or "Unknown Product",
        barcode=barcode,
        quantity=int(overrides.get("quantity", 0)),
        price=float(overrides.get("price", 0.0)),
        category=overrides.get("category", product["category"]),
    )
    inventory.append(item)
    next_id += 1
 
    return jsonify({
        "message": "Product imported from OpenFoodFacts.",
        "item": item.to_dict(),
        "source_data": product,
    }), 201
 
 
# ---------------------------------------------------------------------------
# Search / helper routes
# ---------------------------------------------------------------------------
 
# GET /inventory/search?name=<query> — search by name (case-insensitive)
@app.route("/inventory/search", methods=["GET"])
def search_inventory():
    query = request.args.get("name", "").lower().strip()
    if not query:
        return jsonify({"error": "Provide a 'name' query parameter."}), 400
 
    results = [i.to_dict() for i in inventory if query in i.name.lower()]
    return jsonify(results), 200
 
 
# GET /inventory/category/<category> — filter by category
@app.route("/inventory/category/<category>", methods=["GET"])
def get_by_category(category):
    results = [i.to_dict() for i in inventory
               if i.category.lower() == category.lower()]
    return jsonify(results), 200
 
 
# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
 
if __name__ == "__main__":
    app.run(debug=True)