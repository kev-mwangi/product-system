
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
 
app = Flask(__name__)
CORS(app, resources={r"/inventory*": {"origins": "*"}})
 
inventory = []
next_id = 1
 

OFF_PRODUCT_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
OFF_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
 
 
def fetch_product_details(barcode=None, name=None):
    """
    Query OpenFoodFacts by barcode (exact lookup) or product name (search).
    Returns a dict of extra product details, or None if nothing was found.
    """
    try:
        if barcode:
            res = requests.get(OFF_PRODUCT_URL.format(barcode=barcode), timeout=5)
            res.raise_for_status()
            data = res.json()
 
            if data.get("status") != 1:
                return None
            product = data.get("product", {})
 
        elif name:
            params = {
                "search_terms": name,
                "search_simple": 1,
                "action": "process",
                "json": 1,
                "page_size": 1,
            }
            res = requests.get(OFF_SEARCH_URL, params=params, timeout=5)
            res.raise_for_status()
            data = res.json()
 
            products = data.get("products", [])
            if not products:
                return None
            product = products[0]
 
        else:
            return None
 
        return {
            "product_name": product.get("product_name") or product.get("product_name_en"),
            "brand": product.get("brands"),
            "categories": product.get("categories"),
            "image_url": product.get("image_url"),
            "quantity": product.get("quantity"),
            "barcode": product.get("code"),
            "nutrition_grade": product.get("nutrition_grades"),
        }
 
    except (requests.RequestException, ValueError):
        
        return None
 
 
def find_item(item_id):
    return next((item for item in inventory if item["id"] == item_id), None)
 

 
@app.route("/inventory", methods=["GET"])
def get_inventory():
    return jsonify(inventory), 200
 
 
@app.route("/inventory/<int:item_id>", methods=["GET"])
def get_item(item_id):
    item = find_item(item_id)
    if not item:
        return jsonify({"error": "Item not found"}), 404
    return jsonify(item), 200
 
 
@app.route("/inventory", methods=["POST"])
def add_item():
    global next_id
    data = request.get_json(silent=True) or {}
 
    name = (data.get("name") or "").strip()
    barcode = (data.get("barcode") or "").strip()
    price = data.get("price")
    quantity = data.get("quantity", 1)
    description = (data.get("description") or "").strip()
 
    if not name and not barcode:
        return jsonify({"error": "Provide at least a name or a barcode"}), 400
 
    item = {
        "id": next_id,
        "name": name,
        "barcode": barcode or None,
        "price": price,
        "quantity": quantity,
        "description": description,
    }
 
   
    details = fetch_product_details(barcode=barcode or None, name=None if barcode else name)
    if details:
        item["off_data"] = details
        if not item["name"] and details.get("product_name"):
            item["name"] = details["product_name"]
 
    inventory.append(item)
    next_id += 1
 
    return jsonify(item), 201
 
 
@app.route("/inventory/<int:item_id>", methods=["PATCH"])
def update_item(item_id):
    item = find_item(item_id)
    if not item:
        return jsonify({"error": "Item not found"}), 404
 
    data = request.get_json(silent=True) or {}
 
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "Name cannot be empty"}), 400
        item["name"] = name
 
    if "barcode" in data:
        item["barcode"] = (data.get("barcode") or "").strip() or None
 
    if "price" in data:
        item["price"] = data.get("price")
 
    if "quantity" in data:
        item["quantity"] = data.get("quantity")
 
    if "description" in data:
        item["description"] = (data.get("description") or "").strip()
 
    # If the barcode or name changed, refresh enrichment from OpenFoodFacts
    if "barcode" in data or "name" in data:
        details = fetch_product_details(
            barcode=item.get("barcode"),
            name=None if item.get("barcode") else item.get("name"),
        )
        if details:
            item["off_data"] = details
 
    return jsonify(item), 200
 
 
@app.route("/inventory/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    item = find_item(item_id)
    if not item:
        return jsonify({"error": "Item not found"}), 404
 
    inventory.remove(item)
    return jsonify({"message": "Item deleted"}), 200
 
 
if __name__ == "__main__":
    app.run(debug=True, port=5000)