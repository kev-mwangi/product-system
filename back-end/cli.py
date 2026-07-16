import json
import sys
import requests

BASE_URL = "http://localhost:5000"



def print_item(item):
    print(f"""
  ID       : {item['id']}
  Name     : {item['name']}
  Barcode  : {item['barcode']}
  Category : {item['category']}
  Quantity : {item['quantity']}
  Price    : ${item['price']:.2f}""")


def print_divider(title=""):
    width = 50
    if title:
        pad = (width - len(title) - 2) // 2
        print(f"\n{'─' * pad} {title} {'─' * pad}")
    else:
        print("─" * width)


def safe_get(url, **kwargs):
    try:
        return requests.get(url, **kwargs, timeout=5)
    except requests.exceptions.ConnectionError:
        print("\n Could not connect. Is the Flask server running? (python app.py)")
        sys.exit(1)


def safe_post(url, **kwargs):
    try:
        return requests.post(url, **kwargs, timeout=5)
    except requests.exceptions.ConnectionError:
        print("\n Could not connect. Is the Flask server running? (python app.py)")
        sys.exit(1)


def safe_patch(url, **kwargs):
    try:
        return requests.patch(url, **kwargs, timeout=5)
    except requests.exceptions.ConnectionError:
        print("\nCould not connect. Is the Flask server running? (python app.py)")
        sys.exit(1)


def safe_delete(url, **kwargs):
    try:
        return requests.delete(url, **kwargs, timeout=5)
    except requests.exceptions.ConnectionError:
        print("\n Could not connect. Is the Flask server running? (python app.py)")
        sys.exit(1)




def list_inventory():
    print_divider("All Inventory Items")
    res = safe_get(f"{BASE_URL}/inventory")
    items = res.json()
    if not items:
        print("  (no items in inventory)")
        return
    for item in items:
        print_item(item)
        print_divider()


def view_item():
    print_divider("View Item")
    try:
        item_id = int(input("  Enter item ID: ").strip())
    except ValueError:
        print("    ID must be a number.")
        return

    res = safe_get(f"{BASE_URL}/inventory/{item_id}")
    if res.status_code == 404:
        print(f"   {res.json()['error']}")
        return
    print_item(res.json())


def add_item():
    print_divider("Add New Item")
    name = input("  Name     : ").strip()
    barcode = input("  Barcode  : ").strip()
    category = input("  Category [General]: ").strip() or "General"

    try:
        quantity = int(input("  Quantity : ").strip())
        price = float(input("  Price    : $").strip())
    except ValueError:
        print("    Quantity must be an integer and price must be a number.")
        return

    payload = {
        "name": name,
        "barcode": barcode,
        "quantity": quantity,
        "price": price,
        "category": category,
    }
    res = safe_post(f"{BASE_URL}/inventory", json=payload)

    if res.status_code == 201:
        print("\n   Item added:")
        print_item(res.json())
    else:
        print(f"\n   Error: {res.json().get('error')}")


def edit_item():
    print_divider("Edit Item")
    try:
        item_id = int(input("  Enter item ID to edit: ").strip())
    except ValueError:
        print("   ID must be a number.")
        return

    # Show current values first
    res = safe_get(f"{BASE_URL}/inventory/{item_id}")
    if res.status_code == 404:
        print(f"   {res.json()['error']}")
        return
    current = res.json()
    print("  Current values (press Enter to keep):")
    print_item(current)
    print()

    updates = {}
    name = input(f"  Name [{current['name']}]: ").strip()
    if name:
        updates["name"] = name

    barcode = input(f"  Barcode [{current['barcode']}]: ").strip()
    if barcode:
        updates["barcode"] = barcode

    category = input(f"  Category [{current['category']}]: ").strip()
    if category:
        updates["category"] = category

    qty_str = input(f"  Quantity [{current['quantity']}]: ").strip()
    if qty_str:
        try:
            updates["quantity"] = int(qty_str)
        except ValueError:
            print("    Quantity must be an integer. Skipping.")

    price_str = input(f"  Price [${current['price']:.2f}]: $").strip()
    if price_str:
        try:
            updates["price"] = float(price_str)
        except ValueError:
            print("   Price must be a number. Skipping.")

    if not updates:
        print("  No changes made.")
        return

    res = safe_patch(f"{BASE_URL}/inventory/{item_id}", json=updates)
    if res.status_code == 200:
        print("\n   Item updated:")
        print_item(res.json())
    else:
        print(f"\n    Error: {res.json().get('error')}")


def delete_item():
    print_divider("Delete Item")
    try:
        item_id = int(input("  Enter item ID to delete: ").strip())
    except ValueError:
        print("   ID must be a number.")
        return

    # Confirm
    res = safe_get(f"{BASE_URL}/inventory/{item_id}")
    if res.status_code == 404:
        print(f"   {res.json()['error']}")
        return

    item = res.json()
    print(f"\n  About to delete: {item['name']} (ID {item['id']})")
    confirm = input("  Are you sure? [y/N]: ").strip().lower()
    if confirm != "y":
        print("  Cancelled.")
        return

    res = safe_delete(f"{BASE_URL}/inventory/{item_id}")
    if res.status_code == 204:
        print("   Item deleted.")
    else:
        print(f"   Error: {res.text}")


def search_items():
    print_divider("Search Inventory")
    query = input("  Search by name: ").strip()
    if not query:
        print("    Please enter a search term.")
        return

    res = safe_get(f"{BASE_URL}/inventory/search", params={"name": query})
    items = res.json()
    if not items:
        print(f"  No items matching '{query}'.")
        return
    for item in items:
        print_item(item)
        print_divider()


def lookup_barcode():
    print_divider("Lookup Barcode (OpenFoodFacts)")
    barcode = input("  Enter barcode: ").strip()
    if not barcode:
        print("    Barcode cannot be empty.")
        return

    print(f"    Fetching data for barcode {barcode}...")
    res = safe_get(f"{BASE_URL}/lookup/{barcode}")

    if res.status_code == 404:
        print(f"    {res.json()['error']}")
        return
    if res.status_code != 200:
        print(f"    Error: {res.json().get('error')}")
        return

    product = res.json()
    print(f"""
  Product  : {product['name']}
  Barcode  : {product['barcode']}
  Category : {product['category']}
  Brands   : {product.get('brands', 'N/A')}
  Pack Size: {product.get('quantity_info', 'N/A')}
  Image    : {product.get('image_url', 'N/A')}""")

    # Offer to import
    add = input("\n  Add to inventory? [y/N]: ").strip().lower()
    if add != "y":
        return

    try:
        quantity = int(input("  Quantity: ").strip())
        price = float(input("  Price: $").strip())
    except ValueError:
        print("    Invalid quantity or price.")
        return

    res = safe_post(
        f"{BASE_URL}/lookup/{barcode}/import",
        json={"quantity": quantity, "price": price},
    )
    if res.status_code == 201:
        print("\n    Product imported:")
        print_item(res.json()["item"])
    else:
        print(f"\n    Error: {res.json().get('error')}")




MENU = """

  1. List all inventory
  2. View item by ID
  3. Add new item
  4. Edit item
  5. Delete item
  6. Search by name
  7. Lookup barcode (OpenFoodFacts)
  0. Exit
"""

ACTIONS = {
    "1": list_inventory,
    "2": view_item,
    "3": add_item,
    "4": edit_item,
    "5": delete_item,
    "6": search_items,
    "7": lookup_barcode,
}


def main():
    while True:
        print(MENU)
        choice = input("  Choose an option: ").strip()
        if choice == "0":
            print("\n  Goodbye!\n")
            break
        action = ACTIONS.get(choice)
        if action:
            action()
        else:
            print("    Invalid option. Please choose 0–7.")


if __name__ == "__main__":
    main()