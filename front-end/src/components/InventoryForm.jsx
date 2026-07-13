import { useState, useEffect } from "react";
import "./InventoryForm.css";

const API_URL = "http://localhost:5000/inventory";

function InventoryForm() {
  const [formData, setFormData] = useState({
    name: "",
    barcode: "",
    price: "",
    quantity: "",
    description: "",
  });

  const [inventory, setInventory] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchInventory();
  }, []);

  const fetchInventory = async () => {
    setError("");
    try {
      const res = await fetch(API_URL);
      if (!res.ok) throw new Error("Failed to load inventory");
      const data = await res.json();
      setInventory(data);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!formData.name.trim() && !formData.barcode.trim()) {
      setError("Provide at least a name or a barcode.");
      return;
    }

    const payload = {
      name: formData.name.trim(),
      barcode: formData.barcode.trim(),
      description: formData.description.trim(),
    };
    if (formData.price !== "") payload.price = parseFloat(formData.price);
    if (formData.quantity !== "") payload.quantity = parseInt(formData.quantity, 10);

    setLoading(true);
    try {
      const res = await fetch(
        editingId ? `${API_URL}/${editingId}` : API_URL,
        {
          method: editingId ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }
      );

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || "Request failed");
      }

      await fetchInventory();
      setEditingId(null);
      setFormData({ name: "", barcode: "", price: "", quantity: "", description: "" });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    setError("");
    try {
      const res = await fetch(`${API_URL}/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete item");

      await fetchInventory();

      if (editingId === id) {
        setEditingId(null);
        setFormData({ name: "", barcode: "", price: "", quantity: "", description: "" });
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const handleEdit = (item) => {
    setEditingId(item.id);
    setFormData({
      name: item.name || "",
      barcode: item.barcode || "",
      price: item.price != null ? item.price.toString() : "",
      quantity: item.quantity != null ? item.quantity.toString() : "",
      description: item.description || "",
    });
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setFormData({ name: "", barcode: "", price: "", quantity: "", description: "" });
  };

  return (
    <>
      <div className="header">
        <h1>INVENTORY SYSTEM</h1>
      </div>

      <form onSubmit={handleSubmit}>
        {error && <p className="form-error">{error}</p>}

        <div className="field">
          <label htmlFor="name">Name:</label>
          <input
            type="text"
            id="name"
            name="name"
            value={formData.name}
            onChange={handleChange}
            placeholder="Leave blank if using barcode"
          />
        </div>

        <div className="field">
          <label htmlFor="barcode">Barcode:</label>
          <input
            type="text"
            id="barcode"
            name="barcode"
            value={formData.barcode}
            onChange={handleChange}
            placeholder="Leave blank if using name"
          />
        </div>

        <div className="field field-price">
          <label htmlFor="price">Price:</label>
          <input
            type="number"
            id="price"
            name="price"
            step="0.01"
            value={formData.price}
            onChange={handleChange}
          />
        </div>

        <div className="field">
          <label htmlFor="quantity">Quantity:</label>
          <input
            type="number"
            id="quantity"
            name="quantity"
            step="1"
            value={formData.quantity}
            onChange={handleChange}
          />
        </div>

        <div className="field field-description">
          <label htmlFor="description">Description:</label>
          <textarea
            id="description"
            name="description"
            value={formData.description}
            onChange={handleChange}
          />
        </div>

        <p className="hint">
          Adding by barcode or name automatically looks up extra details on
          OpenFoodFacts.
        </p>

        <div className="form-actions">
          <button type="submit" disabled={loading}>
            {loading ? "Saving..." : editingId ? "Update Item" : "Add Item"}
          </button>
          {editingId && (
            <button type="button" className="cancel-btn" onClick={handleCancelEdit}>
              Cancel
            </button>
          )}
        </div>
      </form>

      <div className="inventory-list">
        {inventory.length === 0 ? (
          <p className="empty-state">No items yet. Add one above.</p>
        ) : (
          <ul>
            {inventory.map((item) => (
              <li
                key={item.id}
                className={`inventory-item${editingId === item.id ? " editing" : ""}`}
              >
                {item.off_data?.image_url && (
                  <img
                    className="item-thumb"
                    src={item.off_data.image_url}
                    alt={item.name}
                  />
                )}

                <div className="item-info">
                  <span className="item-name">{item.name || "(unnamed)"}</span>
                  <span className="item-meta">
                    {item.price != null && <span className="item-price">${Number(item.price).toFixed(2)}</span>}
                    {item.quantity != null && <span className="item-qty">qty: {item.quantity}</span>}
                    {item.barcode && <span className="item-barcode">{item.barcode}</span>}
                  </span>

                  {item.description && (
                    <p className="item-description">{item.description}</p>
                  )}

                  {item.off_data && (
                    <div className="off-data">
                      {item.off_data.brand && (
                        <span className="tag">{item.off_data.brand}</span>
                      )}
                      {item.off_data.nutrition_grade && (
                        <span className="tag tag-grade">
                          Nutri-Score {item.off_data.nutrition_grade.toUpperCase()}
                        </span>
                      )}
                      {item.off_data.quantity && (
                        <span className="tag">{item.off_data.quantity}</span>
                      )}
                    </div>
                  )}
                </div>

                <div className="item-actions">
                  <button type="button" className="edit-btn" onClick={() => handleEdit(item)}>
                    Edit
                  </button>
                  <button type="button" className="delete-btn" onClick={() => handleDelete(item.id)}>
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
}

export default InventoryForm;