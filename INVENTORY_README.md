# Inventory Management System

A comprehensive Python inventory management system for tracking products, quantities, and related information.

## Features

- **Product Management**: Add, remove, and update products
- **Quantity Tracking**: Track and update product quantities with validation
- **Price Management**: Update product prices with validation
- **Search & Filter**: Search products by name/description and filter by category
- **Low Stock Alerts**: Identify products below a specified threshold
- **Inventory Analytics**: Calculate total inventory value and get summary statistics
- **Data Persistence**: Import/export inventory data in JSON format
- **Category Management**: Organize products by categories

## Installation

No external dependencies required. The system uses Python's standard library.

```bash
# Simply copy the inventory.py file to your project
# Or clone this repository
```

## Quick Start

### Basic Usage

```python
from inventory import InventoryManager

# Create an inventory manager
inventory = InventoryManager()

# Add products
inventory.add_product(
    product_id="PROD001",
    name="Laptop",
    quantity=15,
    price=999.99,
    category="Electronics",
    description="High-performance laptop"
)

# List all products
products = inventory.list_products()
for product in products:
    print(f"{product.name}: {product.quantity} units @ ${product.price}")

# Update quantity
inventory.update_quantity("PROD001", -5)  # Sold 5 laptops

# Search for products
results = inventory.search_products("laptop")

# Get low stock items
low_stock = inventory.get_low_stock_products(threshold=10)
```

## API Reference

### InventoryManager Class

#### Methods

##### `add_product(product_id, name, quantity, price, category="General", description="")`
Add a new product to the inventory.

**Parameters:**
- `product_id` (str): Unique identifier for the product
- `name` (str): Product name
- `quantity` (int): Initial quantity (must be >= 0)
- `price` (float): Product price (must be >= 0)
- `category` (str, optional): Product category
- `description` (str, optional): Product description

**Returns:** Product object

**Raises:** 
- `ValueError`: If product_id already exists, or if quantity/price is negative

##### `remove_product(product_id)`
Remove a product from the inventory.

**Parameters:**
- `product_id` (str): ID of the product to remove

**Returns:** `True` if removed, `False` if not found

##### `update_quantity(product_id, quantity_change)`
Update the quantity of a product.

**Parameters:**
- `product_id` (str): ID of the product
- `quantity_change` (int): Amount to add (positive) or remove (negative)

**Returns:** Updated Product object or `None` if not found

**Raises:**
- `ValueError`: If resulting quantity would be negative

##### `update_price(product_id, new_price)`
Update the price of a product.

**Parameters:**
- `product_id` (str): ID of the product
- `new_price` (float): New price (must be >= 0)

**Returns:** Updated Product object or `None` if not found

**Raises:**
- `ValueError`: If price is negative

##### `get_product(product_id)`
Get a product by ID.

**Parameters:**
- `product_id` (str): ID of the product

**Returns:** Product object or `None` if not found

##### `list_products(category=None)`
List all products, optionally filtered by category.

**Parameters:**
- `category` (str, optional): Category filter

**Returns:** List of Product objects

##### `search_products(search_term)`
Search for products by name or description (case-insensitive).

**Parameters:**
- `search_term` (str): Term to search for

**Returns:** List of matching Product objects

##### `get_low_stock_products(threshold=10)`
Get products with quantity below threshold.

**Parameters:**
- `threshold` (int, optional): Quantity threshold (default: 10)

**Returns:** List of products with low stock

##### `get_total_value(category=None)`
Calculate total inventory value.

**Parameters:**
- `category` (str, optional): Category filter

**Returns:** Total value (float)

##### `get_categories()`
Get list of all unique categories.

**Returns:** Sorted list of category names

##### `export_to_json()`
Export inventory to JSON string.

**Returns:** JSON string representation of inventory

##### `import_from_json(json_str)`
Import inventory from JSON string.

**Parameters:**
- `json_str` (str): JSON string containing inventory data

**Returns:** Number of products imported (int)

##### `get_inventory_summary()`
Get a summary of the inventory.

**Returns:** Dictionary with inventory statistics:
- `total_products`: Total number of unique products
- `total_quantity`: Total number of items
- `total_value`: Total inventory value
- `categories`: Number of categories
- `low_stock_items`: Number of low stock items
- `categories_list`: List of category names

## Examples

### Example 1: Basic Inventory Operations

```python
from inventory import InventoryManager

# Initialize
inventory = InventoryManager()

# Add products
inventory.add_product("SKU001", "Wireless Mouse", 50, 29.99, "Electronics")
inventory.add_product("SKU002", "USB Cable", 100, 9.99, "Electronics")
inventory.add_product("SKU003", "Desk Lamp", 20, 39.99, "Furniture")

# Update inventory
inventory.update_quantity("SKU001", -10)  # Sold 10 mice
inventory.update_price("SKU003", 34.99)   # Price reduction

# Check stock
low_stock = inventory.get_low_stock_products(25)
for product in low_stock:
    print(f"Low stock alert: {product.name} ({product.quantity} remaining)")
```

### Example 2: Inventory Analytics

```python
# Get summary
summary = inventory.get_inventory_summary()
print(f"Total Products: {summary['total_products']}")
print(f"Total Value: ${summary['total_value']:.2f}")
print(f"Categories: {', '.join(summary['categories_list'])}")

# Calculate value by category
electronics_value = inventory.get_total_value("Electronics")
print(f"Electronics Inventory Value: ${electronics_value:.2f}")
```

### Example 3: Data Persistence

```python
# Export inventory
json_data = inventory.export_to_json()
with open('inventory_backup.json', 'w') as f:
    f.write(json_data)

# Import inventory
with open('inventory_backup.json', 'r') as f:
    json_data = f.read()
inventory.import_from_json(json_data)
```

### Example 4: Search and Filter

```python
# Search by keyword
results = inventory.search_products("wireless")
for product in results:
    print(f"Found: {product.name}")

# Filter by category
electronics = inventory.list_products("Electronics")
print(f"Electronics items: {len(electronics)}")
```

## Running Tests

The system includes comprehensive unit tests:

```bash
# Run all tests
python -m unittest test_inventory.py -v

# Or with pytest (if installed)
pytest test_inventory.py -v
```

## Running the Demo

```bash
python inventory.py
```

This will demonstrate all major features of the inventory system.

## Product Class

Each product in the inventory is represented by a `Product` object with the following attributes:

- `id` (str): Unique product identifier
- `name` (str): Product name
- `quantity` (int): Current quantity in stock
- `price` (float): Product price
- `category` (str): Product category
- `description` (str): Product description
- `added_date` (str): ISO format timestamp when product was added
- `last_updated` (str): ISO format timestamp of last update

## Error Handling

The system includes validation and error handling:

- Duplicate product IDs are prevented
- Negative quantities and prices are not allowed
- Insufficient quantity errors when trying to remove more items than available
- Graceful handling of non-existent product IDs

## Best Practices

1. **Use Unique Product IDs**: Ensure each product has a unique identifier (SKU, barcode, etc.)
2. **Regular Backups**: Use `export_to_json()` regularly to backup inventory data
3. **Monitor Low Stock**: Regularly check `get_low_stock_products()` to avoid stockouts
4. **Categorize Products**: Use meaningful categories for better organization
5. **Validate Operations**: Check return values from operations (e.g., `None` means product not found)

## Integration Ideas

This inventory system can be integrated with:

- Web applications (Flask, Django)
- E-commerce platforms
- Point-of-sale systems
- Supply chain management systems
- Accounting software
- Barcode/QR code scanners

## License

This code is provided as-is for educational and commercial use.

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests.
