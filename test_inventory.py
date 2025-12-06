"""
Unit tests for the Inventory Management System
"""

import unittest
import json
from inventory import InventoryManager, Product


class TestProduct(unittest.TestCase):
    """Test cases for the Product class."""
    
    def test_product_creation(self):
        """Test creating a product."""
        product = Product(
            id="TEST001",
            name="Test Product",
            quantity=10,
            price=99.99,
            category="Test",
            description="A test product"
        )
        
        self.assertEqual(product.id, "TEST001")
        self.assertEqual(product.name, "Test Product")
        self.assertEqual(product.quantity, 10)
        self.assertEqual(product.price, 99.99)
        self.assertEqual(product.category, "Test")
        self.assertEqual(product.description, "A test product")
    
    def test_product_to_dict(self):
        """Test converting product to dictionary."""
        product = Product(
            id="TEST001",
            name="Test Product",
            quantity=10,
            price=99.99
        )
        
        product_dict = product.to_dict()
        
        self.assertEqual(product_dict['id'], "TEST001")
        self.assertEqual(product_dict['name'], "Test Product")
        self.assertEqual(product_dict['quantity'], 10)
        self.assertEqual(product_dict['price'], 99.99)
        self.assertIn('added_date', product_dict)
        self.assertIn('last_updated', product_dict)
    
    def test_product_from_dict(self):
        """Test creating product from dictionary."""
        data = {
            'id': 'TEST001',
            'name': 'Test Product',
            'quantity': 10,
            'price': 99.99,
            'category': 'Test',
            'description': 'A test product',
            'added_date': '2024-01-01T00:00:00',
            'last_updated': '2024-01-01T00:00:00'
        }
        
        product = Product.from_dict(data)
        
        self.assertEqual(product.id, "TEST001")
        self.assertEqual(product.name, "Test Product")
        self.assertEqual(product.quantity, 10)


class TestInventoryManager(unittest.TestCase):
    """Test cases for the InventoryManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.inventory = InventoryManager()
    
    def test_add_product(self):
        """Test adding a product to inventory."""
        product = self.inventory.add_product(
            "PROD001",
            "Test Product",
            10,
            99.99,
            "Test",
            "A test product"
        )
        
        self.assertEqual(product.id, "PROD001")
        self.assertEqual(product.name, "Test Product")
        self.assertEqual(len(self.inventory.products), 1)
    
    def test_add_duplicate_product(self):
        """Test that adding duplicate product raises error."""
        self.inventory.add_product("PROD001", "Product 1", 10, 99.99)
        
        with self.assertRaises(ValueError) as context:
            self.inventory.add_product("PROD001", "Product 2", 20, 199.99)
        
        self.assertIn("already exists", str(context.exception))
    
    def test_add_product_negative_quantity(self):
        """Test that negative quantity raises error."""
        with self.assertRaises(ValueError) as context:
            self.inventory.add_product("PROD001", "Product", -5, 99.99)
        
        self.assertIn("cannot be negative", str(context.exception))
    
    def test_add_product_negative_price(self):
        """Test that negative price raises error."""
        with self.assertRaises(ValueError) as context:
            self.inventory.add_product("PROD001", "Product", 10, -99.99)
        
        self.assertIn("cannot be negative", str(context.exception))
    
    def test_remove_product(self):
        """Test removing a product from inventory."""
        self.inventory.add_product("PROD001", "Product", 10, 99.99)
        
        result = self.inventory.remove_product("PROD001")
        
        self.assertTrue(result)
        self.assertEqual(len(self.inventory.products), 0)
    
    def test_remove_nonexistent_product(self):
        """Test removing a product that doesn't exist."""
        result = self.inventory.remove_product("NONEXISTENT")
        
        self.assertFalse(result)
    
    def test_update_quantity_increase(self):
        """Test increasing product quantity."""
        self.inventory.add_product("PROD001", "Product", 10, 99.99)
        
        product = self.inventory.update_quantity("PROD001", 5)
        
        self.assertIsNotNone(product)
        self.assertEqual(product.quantity, 15)
    
    def test_update_quantity_decrease(self):
        """Test decreasing product quantity."""
        self.inventory.add_product("PROD001", "Product", 10, 99.99)
        
        product = self.inventory.update_quantity("PROD001", -3)
        
        self.assertIsNotNone(product)
        self.assertEqual(product.quantity, 7)
    
    def test_update_quantity_negative_result(self):
        """Test that quantity cannot go below zero."""
        self.inventory.add_product("PROD001", "Product", 5, 99.99)
        
        with self.assertRaises(ValueError) as context:
            self.inventory.update_quantity("PROD001", -10)
        
        self.assertIn("Insufficient quantity", str(context.exception))
    
    def test_update_quantity_nonexistent_product(self):
        """Test updating quantity for nonexistent product."""
        result = self.inventory.update_quantity("NONEXISTENT", 5)
        
        self.assertIsNone(result)
    
    def test_update_price(self):
        """Test updating product price."""
        self.inventory.add_product("PROD001", "Product", 10, 99.99)
        
        product = self.inventory.update_price("PROD001", 149.99)
        
        self.assertIsNotNone(product)
        self.assertEqual(product.price, 149.99)
    
    def test_update_price_negative(self):
        """Test that negative price raises error."""
        self.inventory.add_product("PROD001", "Product", 10, 99.99)
        
        with self.assertRaises(ValueError) as context:
            self.inventory.update_price("PROD001", -50)
        
        self.assertIn("cannot be negative", str(context.exception))
    
    def test_update_price_nonexistent_product(self):
        """Test updating price for nonexistent product."""
        result = self.inventory.update_price("NONEXISTENT", 99.99)
        
        self.assertIsNone(result)
    
    def test_get_product(self):
        """Test getting a product by ID."""
        self.inventory.add_product("PROD001", "Product", 10, 99.99)
        
        product = self.inventory.get_product("PROD001")
        
        self.assertIsNotNone(product)
        self.assertEqual(product.id, "PROD001")
    
    def test_get_nonexistent_product(self):
        """Test getting a nonexistent product."""
        product = self.inventory.get_product("NONEXISTENT")
        
        self.assertIsNone(product)
    
    def test_list_products(self):
        """Test listing all products."""
        self.inventory.add_product("PROD001", "Product 1", 10, 99.99, "Electronics")
        self.inventory.add_product("PROD002", "Product 2", 20, 199.99, "Furniture")
        
        products = self.inventory.list_products()
        
        self.assertEqual(len(products), 2)
    
    def test_list_products_by_category(self):
        """Test listing products filtered by category."""
        self.inventory.add_product("PROD001", "Product 1", 10, 99.99, "Electronics")
        self.inventory.add_product("PROD002", "Product 2", 20, 199.99, "Electronics")
        self.inventory.add_product("PROD003", "Product 3", 15, 149.99, "Furniture")
        
        electronics = self.inventory.list_products("Electronics")
        
        self.assertEqual(len(electronics), 2)
        for product in electronics:
            self.assertEqual(product.category, "Electronics")
    
    def test_search_products_by_name(self):
        """Test searching products by name."""
        self.inventory.add_product("PROD001", "Laptop Computer", 10, 999.99)
        self.inventory.add_product("PROD002", "Desktop Computer", 5, 799.99)
        self.inventory.add_product("PROD003", "Mouse", 50, 29.99)
        
        results = self.inventory.search_products("computer")
        
        self.assertEqual(len(results), 2)
    
    def test_search_products_by_description(self):
        """Test searching products by description."""
        self.inventory.add_product("PROD001", "Product 1", 10, 99.99, 
                                   description="High quality item")
        self.inventory.add_product("PROD002", "Product 2", 20, 199.99, 
                                   description="Premium quality item")
        self.inventory.add_product("PROD003", "Product 3", 15, 149.99, 
                                   description="Standard item")
        
        results = self.inventory.search_products("quality")
        
        self.assertEqual(len(results), 2)
    
    def test_search_products_case_insensitive(self):
        """Test that search is case-insensitive."""
        self.inventory.add_product("PROD001", "Laptop", 10, 999.99)
        
        results_lower = self.inventory.search_products("laptop")
        results_upper = self.inventory.search_products("LAPTOP")
        results_mixed = self.inventory.search_products("LaPtOp")
        
        self.assertEqual(len(results_lower), 1)
        self.assertEqual(len(results_upper), 1)
        self.assertEqual(len(results_mixed), 1)
    
    def test_get_low_stock_products(self):
        """Test getting low stock products."""
        self.inventory.add_product("PROD001", "Product 1", 5, 99.99)
        self.inventory.add_product("PROD002", "Product 2", 15, 199.99)
        self.inventory.add_product("PROD003", "Product 3", 8, 149.99)
        
        low_stock = self.inventory.get_low_stock_products(10)
        
        self.assertEqual(len(low_stock), 2)
        for product in low_stock:
            self.assertLess(product.quantity, 10)
    
    def test_get_low_stock_products_custom_threshold(self):
        """Test getting low stock products with custom threshold."""
        self.inventory.add_product("PROD001", "Product 1", 3, 99.99)
        self.inventory.add_product("PROD002", "Product 2", 7, 199.99)
        
        low_stock = self.inventory.get_low_stock_products(5)
        
        self.assertEqual(len(low_stock), 1)
        self.assertEqual(low_stock[0].id, "PROD001")
    
    def test_get_total_value(self):
        """Test calculating total inventory value."""
        self.inventory.add_product("PROD001", "Product 1", 10, 100.00)
        self.inventory.add_product("PROD002", "Product 2", 5, 50.00)
        
        total = self.inventory.get_total_value()
        
        self.assertEqual(total, 1250.00)  # (10 * 100) + (5 * 50)
    
    def test_get_total_value_by_category(self):
        """Test calculating total value by category."""
        self.inventory.add_product("PROD001", "Product 1", 10, 100.00, "Electronics")
        self.inventory.add_product("PROD002", "Product 2", 5, 50.00, "Electronics")
        self.inventory.add_product("PROD003", "Product 3", 8, 75.00, "Furniture")
        
        electronics_value = self.inventory.get_total_value("Electronics")
        
        self.assertEqual(electronics_value, 1250.00)
    
    def test_get_categories(self):
        """Test getting list of categories."""
        self.inventory.add_product("PROD001", "Product 1", 10, 99.99, "Electronics")
        self.inventory.add_product("PROD002", "Product 2", 20, 199.99, "Furniture")
        self.inventory.add_product("PROD003", "Product 3", 15, 149.99, "Electronics")
        
        categories = self.inventory.get_categories()
        
        self.assertEqual(len(categories), 2)
        self.assertIn("Electronics", categories)
        self.assertIn("Furniture", categories)
    
    def test_export_to_json(self):
        """Test exporting inventory to JSON."""
        self.inventory.add_product("PROD001", "Product 1", 10, 99.99)
        
        json_str = self.inventory.export_to_json()
        data = json.loads(json_str)
        
        self.assertIn('products', data)
        self.assertIn('export_date', data)
        self.assertEqual(len(data['products']), 1)
        self.assertEqual(data['products'][0]['id'], 'PROD001')
    
    def test_import_from_json(self):
        """Test importing inventory from JSON."""
        json_data = {
            'products': [
                {
                    'id': 'PROD001',
                    'name': 'Product 1',
                    'quantity': 10,
                    'price': 99.99,
                    'category': 'Test',
                    'description': 'Test product',
                    'added_date': '2024-01-01T00:00:00',
                    'last_updated': '2024-01-01T00:00:00'
                }
            ],
            'export_date': '2024-01-01T00:00:00'
        }
        
        json_str = json.dumps(json_data)
        count = self.inventory.import_from_json(json_str)
        
        self.assertEqual(count, 1)
        self.assertEqual(len(self.inventory.products), 1)
        
        product = self.inventory.get_product("PROD001")
        self.assertIsNotNone(product)
        self.assertEqual(product.name, "Product 1")
    
    def test_get_inventory_summary(self):
        """Test getting inventory summary."""
        self.inventory.add_product("PROD001", "Product 1", 10, 100.00, "Electronics")
        self.inventory.add_product("PROD002", "Product 2", 5, 50.00, "Electronics")
        self.inventory.add_product("PROD003", "Product 3", 8, 75.00, "Furniture")
        
        summary = self.inventory.get_inventory_summary()
        
        self.assertEqual(summary['total_products'], 3)
        self.assertEqual(summary['total_quantity'], 23)
        self.assertEqual(summary['total_value'], 1850.00)
        self.assertEqual(summary['categories'], 2)
        self.assertIn('categories_list', summary)
        self.assertIn('low_stock_items', summary)


if __name__ == "__main__":
    unittest.main()
