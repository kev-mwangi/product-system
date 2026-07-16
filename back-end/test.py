

import json
import pytest
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(_file_)))

import app as app_module
from app import app, inventory, Item




@pytest.fixture
def client():
    """Flask test client with a clean inventory for every test."""
    app.config["TESTING"] = True

    with app.test_client() as client:
        # Reset inventory and counter to a known state before each test
        inventory.clear()
        inventory.extend([
            Item(1, "Coca-Cola 500ml", "5449000000996", 50, 1.99, "Beverages"),
            Item(2, "Lays Classic Chips", "0028400315012", 30, 2.49, "Snacks"),
            Item(3, "Minute Maid Orange", "0025000056954", 20, 1.79, "Beverages"),
        ])
        app_module.next_id = 4
        yield client




class TestGetInventory:
    def test_returns_200(self, client):
        res = client.get("/inventory")
        assert res.status_code == 200

    def test_returns_all_items(self, client):
        data = res = client.get("/inventory").get_json()
        assert len(data) == 3

    def test_item_structure(self, client):
        data = client.get("/inventory").get_json()
        item = data[0]
        for key in ("id", "name", "barcode", "quantity", "price", "category"):
            assert key in item



class TestGetSingleItem:
    def test_returns_correct_item(self, client):
        res = client.get("/inventory/1")
        assert res.status_code == 200
        data = res.get_json()
        assert data["id"] == 1
        assert data["name"] == "Coca-Cola 500ml"

    def test_returns_404_for_missing_id(self, client):
        res = client.get("/inventory/999")
        assert res.status_code == 404

    def test_404_contains_error_message(self, client):
        res = client.get("/inventory/999")
        data = res.get_json()
        assert "error" in data


# ---------------------------------------------------------------------------
# POST /inventory
# ---------------------------------------------------------------------------

class TestCreateItem:
    def test_creates_item_successfully(self, client):
        payload = {
            "name": "Test Drink",
            "barcode": "1234567890123",
            "quantity": 10,
            "price": 3.50,
            "category": "Beverages",
        }
        res = client.post("/inventory", json=payload)
        assert res.status_code == 201

    def test_returns_created_item(self, client):
        payload = {
            "name": "Test Drink",
            "barcode": "1234567890123",
            "quantity": 10,
            "price": 3.50,
        }
        data = client.post("/inventory", json=payload).get_json()
        assert data["name"] == "Test Drink"
        assert data["quantity"] == 10
        assert data["price"] == 3.50

    def test_item_appears_in_inventory(self, client):
        payload = {
            "name": "New Item",
            "barcode": "111",
            "quantity": 5,
            "price": 1.00,
        }
        client.post("/inventory", json=payload)
        all_items = client.get("/inventory").get_json()
        names = [i["name"] for i in all_items]
        assert "New Item" in names

    def test_missing_name_returns_400(self, client):
        res = client.post("/inventory", json={"barcode": "111", "quantity": 1, "price": 1.0})
        assert res.status_code == 400

    def test_missing_price_returns_400(self, client):
        res = client.post("/inventory", json={"name": "x", "barcode": "111", "quantity": 1})
        assert res.status_code == 400

    def test_invalid_quantity_returns_400(self, client):
        res = client.post("/inventory", json={
            "name": "x", "barcode": "111", "quantity": "abc", "price": 1.0
        })
        assert res.status_code == 400

    def test_invalid_price_returns_400(self, client):
        res = client.post("/inventory", json={
            "name": "x", "barcode": "111", "quantity": 1, "price": "not-a-price"
        })
        assert res.status_code == 400

    def test_default_category_is_general(self, client):
        payload = {"name": "No Cat", "barcode": "000", "quantity": 1, "price": 1.0}
        data = client.post("/inventory", json=payload).get_json()
        assert data["category"] == "General"

    def test_ids_auto_increment(self, client):
        payload = {"name": "A", "barcode": "1", "quantity": 1, "price": 1.0}
        d1 = client.post("/inventory", json=payload).get_json()
        d2 = client.post("/inventory", json=payload).get_json()
        assert d2["id"] == d1["id"] + 1


# ---------------------------------------------------------------------------
# PATCH /inventory/<id>
# ---------------------------------------------------------------------------

class TestUpdateItem:
    def test_updates_name(self, client):
        res = client.patch("/inventory/1", json={"name": "Pepsi Max"})
        assert res.status_code == 200
        assert res.get_json()["name"] == "Pepsi Max"

    def test_updates_quantity(self, client):
        res = client.patch("/inventory/1", json={"quantity": 99})
        assert res.get_json()["quantity"] == 99

    def test_updates_price(self, client):
        res = client.patch("/inventory/1", json={"price": 9.99})
        assert res.get_json()["price"] == 9.99

    def test_partial_update_keeps_other_fields(self, client):
        client.patch("/inventory/1", json={"name": "Changed Name"})
        item = client.get("/inventory/1").get_json()
        # barcode and other fields should be untouched
        assert item["barcode"] == "5449000000996"

    def test_returns_404_for_missing_id(self, client):
        res = client.patch("/inventory/999", json={"name": "x"})
        assert res.status_code == 404

    def test_invalid_quantity_returns_400(self, client):
        res = client.patch("/inventory/1", json={"quantity": "many"})
        assert res.status_code == 400

    def test_empty_body_returns_400(self, client):
        res = client.patch("/inventory/1", data="", content_type="application/json")
        assert res.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /inventory/<id>
# ---------------------------------------------------------------------------

class TestDeleteItem:
    def test_delete_returns_204(self, client):
        res = client.delete("/inventory/1")
        assert res.status_code == 204

    def test_item_removed_from_inventory(self, client):
        client.delete("/inventory/1")
        res = client.get("/inventory/1")
        assert res.status_code == 404

    def test_inventory_count_decreases(self, client):
        before = len(client.get("/inventory").get_json())
        client.delete("/inventory/1")
        after = len(client.get("/inventory").get_json())
        assert after == before - 1

    def test_delete_missing_id_returns_404(self, client):
        res = client.delete("/inventory/999")
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# GET /inventory/search
# ---------------------------------------------------------------------------

class TestSearch:
    def test_finds_matching_items(self, client):
        res = client.get("/inventory/search?name=coca")
        assert res.status_code == 200
        data = res.get_json()
        assert any("Coca" in i["name"] for i in data)

    def test_case_insensitive(self, client):
        res = client.get("/inventory/search?name=LAYS")
        data = res.get_json()
        assert len(data) >= 1

    def test_no_results_returns_empty_list(self, client):
        res = client.get("/inventory/search?name=zzznomatch")
        assert res.get_json() == []

    def test_missing_param_returns_400(self, client):
        res = client.get("/inventory/search")
        assert res.status_code == 400


# ---------------------------------------------------------------------------
# GET /inventory/category/<category>
# ---------------------------------------------------------------------------

class TestCategoryFilter:
    def test_filters_by_category(self, client):
        res = client.get("/inventory/category/Beverages")
        data = res.get_json()
        assert all(i["category"] == "Beverages" for i in data)

    def test_case_insensitive(self, client):
        res = client.get("/inventory/category/beverages")
        data = res.get_json()
        assert len(data) >= 1

    def test_unknown_category_returns_empty(self, client):
        res = client.get("/inventory/category/Electronics")
        assert res.get_json() == []


# ---------------------------------------------------------------------------
# GET /lookup/<barcode> — mocked external API
# ---------------------------------------------------------------------------

MOCK_OFF_RESPONSE = {
    "status": 1,
    "product": {
        "product_name": "Nutella",
        "categories_tags": ["en:spreads"],
        "image_url": "https://example.com/nutella.jpg",
        "brands": "Ferrero",
        "quantity": "400g",
    },
}


class TestLookupBarcode:
    @patch("app.http_requests.get")
    def test_successful_lookup(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_OFF_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        res = client.get("/lookup/3017620422003")
        assert res.status_code == 200
        data = res.get_json()
        assert data["name"] == "Nutella"

    @patch("app.http_requests.get")
    def test_not_found_barcode_returns_404(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": 0}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        res = client.get("/lookup/0000000000000")
        assert res.status_code == 404

    @patch("app.http_requests.get")
    def test_network_error_returns_502(self, mock_get, client):
        import requests as rq
        mock_get.side_effect = rq.exceptions.ConnectionError("timeout")

        res = client.get("/lookup/3017620422003")
        assert res.status_code == 502


# ---------------------------------------------------------------------------
# POST /lookup/<barcode>/import — mocked external API
# ---------------------------------------------------------------------------

class TestImportBarcode:
    @patch("app.http_requests.get")
    def test_import_adds_to_inventory(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_OFF_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        before = len(client.get("/inventory").get_json())
        client.post("/lookup/3017620422003/import", json={"quantity": 5, "price": 4.99})
        after = len(client.get("/inventory").get_json())
        assert after == before + 1

    @patch("app.http_requests.get")
    def test_import_returns_201(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_OFF_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        res = client.post("/lookup/3017620422003/import", json={"quantity": 5, "price": 4.99})
        assert res.status_code == 201

    @patch("app.http_requests.get")
    def test_import_uses_correct_price_quantity(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_OFF_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        res = client.post("/lookup/3017620422003/import", json={"quantity": 12, "price": 7.50})
        item = res.get_json()["item"]
        assert item["quantity"] == 12
        assert item["price"] == 7.50