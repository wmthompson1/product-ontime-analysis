"""
Inventory Management System

A simple and efficient inventory management system for tracking products,
quantities, and related information.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class Product:
    """Represents a product in the inventory system."""
    
    id: str
    name: str
    quantity: int
    price: float
    category: str = "General"
    description: str = ""
    added_date: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert product to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'quantity': self.quantity,
            'price': self.price,
            'category': self.category,
            'description': self.description,
            'added_date': self.added_date,
            'last_updated': self.last_updated
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Product':
        """Create product from dictionary."""
        return cls(**data)


class InventoryManager:
    """Main inventory management class for handling product operations."""
    
    def __init__(self):
        """Initialize the inventory manager."""
        self.products: Dict[str, Product] = {}
    
    def add_product(self, product_id: str, name: str, quantity: int, 
                   price: float, category: str = "General", 
                   description: str = "") -> Product:
        """
        Add a new product to the inventory.
        
        Args:
            product_id: Unique identifier for the product
            name: Product name
            quantity: Initial quantity
            price: Product price
            category: Product category (default: "General")
            description: Product description (default: "")
            
        Returns:
            The created Product object
            
        Raises:
            ValueError: If product_id already exists
        """
        if product_id in self.products:
            raise ValueError(f"Product with ID '{product_id}' already exists")
        
        if quantity < 0:
            raise ValueError("Quantity cannot be negative")
        
        if price < 0:
            raise ValueError("Price cannot be negative")
        
        product = Product(
            id=product_id,
            name=name,
            quantity=quantity,
            price=price,
            category=category,
            description=description
        )
        
        self.products[product_id] = product
        return product
    
    def remove_product(self, product_id: str) -> bool:
        """
        Remove a product from the inventory.
        
        Args:
            product_id: ID of the product to remove
            
        Returns:
            True if product was removed, False if not found
        """
        if product_id in self.products:
            del self.products[product_id]
            return True
        return False
    
    def update_quantity(self, product_id: str, quantity_change: int) -> Optional[Product]:
        """
        Update the quantity of a product.
        
        Args:
            product_id: ID of the product
            quantity_change: Amount to add (positive) or remove (negative)
            
        Returns:
            Updated Product object, or None if product not found
            
        Raises:
            ValueError: If resulting quantity would be negative
        """
        product = self.products.get(product_id)
        if not product:
            return None
        
        new_quantity = product.quantity + quantity_change
        if new_quantity < 0:
            raise ValueError(f"Insufficient quantity. Current: {product.quantity}, Requested change: {quantity_change}")
        
        product.quantity = new_quantity
        product.last_updated = datetime.now().isoformat()
        return product
    
    def update_price(self, product_id: str, new_price: float) -> Optional[Product]:
        """
        Update the price of a product.
        
        Args:
            product_id: ID of the product
            new_price: New price for the product
            
        Returns:
            Updated Product object, or None if product not found
            
        Raises:
            ValueError: If price is negative
        """
        if new_price < 0:
            raise ValueError("Price cannot be negative")
        
        product = self.products.get(product_id)
        if not product:
            return None
        
        product.price = new_price
        product.last_updated = datetime.now().isoformat()
        return product
    
    def get_product(self, product_id: str) -> Optional[Product]:
        """
        Get a product by ID.
        
        Args:
            product_id: ID of the product
            
        Returns:
            Product object if found, None otherwise
        """
        return self.products.get(product_id)
    
    def list_products(self, category: Optional[str] = None) -> List[Product]:
        """
        List all products, optionally filtered by category.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of Product objects
        """
        if category:
            return [p for p in self.products.values() if p.category == category]
        return list(self.products.values())
    
    def search_products(self, search_term: str) -> List[Product]:
        """
        Search for products by name or description.
        
        Args:
            search_term: Term to search for (case-insensitive)
            
        Returns:
            List of matching Product objects
        """
        search_lower = search_term.lower()
        return [
            p for p in self.products.values()
            if search_lower in p.name.lower() or search_lower in p.description.lower()
        ]
    
    def get_low_stock_products(self, threshold: int = 10) -> List[Product]:
        """
        Get products with quantity below threshold.
        
        Args:
            threshold: Quantity threshold (default: 10)
            
        Returns:
            List of products with low stock
        """
        return [p for p in self.products.values() if p.quantity < threshold]
    
    def get_total_value(self, category: Optional[str] = None) -> float:
        """
        Calculate total inventory value.
        
        Args:
            category: Optional category filter
            
        Returns:
            Total value of inventory
        """
        products = self.list_products(category)
        return sum(p.quantity * p.price for p in products)
    
    def get_categories(self) -> List[str]:
        """
        Get list of all unique categories.
        
        Returns:
            List of category names
        """
        return sorted(set(p.category for p in self.products.values()))
    
    def export_to_json(self) -> str:
        """
        Export inventory to JSON string.
        
        Returns:
            JSON representation of inventory
        """
        data = {
            'products': [p.to_dict() for p in self.products.values()],
            'export_date': datetime.now().isoformat()
        }
        return json.dumps(data, indent=2)
    
    def import_from_json(self, json_str: str) -> int:
        """
        Import inventory from JSON string.
        
        Args:
            json_str: JSON string containing inventory data
            
        Returns:
            Number of products imported
        """
        data = json.loads(json_str)
        products_data = data.get('products', [])
        
        count = 0
        for product_data in products_data:
            product = Product.from_dict(product_data)
            self.products[product.id] = product
            count += 1
        
        return count
    
    def get_inventory_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the inventory.
        
        Returns:
            Dictionary with inventory statistics
        """
        products = list(self.products.values())
        
        return {
            'total_products': len(products),
            'total_quantity': sum(p.quantity for p in products),
            'total_value': self.get_total_value(),
            'categories': len(self.get_categories()),
            'low_stock_items': len(self.get_low_stock_products()),
            'categories_list': self.get_categories()
        }


def demo():
    """Demonstrate the inventory management system."""
    print("=== Inventory Management System Demo ===\n")
    
    # Create inventory manager
    inventory = InventoryManager()
    
    # Add products
    print("1. Adding products...")
    inventory.add_product("PROD001", "Laptop", 15, 999.99, "Electronics", "High-performance laptop")
    inventory.add_product("PROD002", "Mouse", 50, 29.99, "Electronics", "Wireless mouse")
    inventory.add_product("PROD003", "Desk Chair", 8, 199.99, "Furniture", "Ergonomic office chair")
    inventory.add_product("PROD004", "Notebook", 100, 3.99, "Stationery", "Spiral notebook")
    print("✓ Products added successfully\n")
    
    # List all products
    print("2. Listing all products:")
    for product in inventory.list_products():
        print(f"  - {product.name} ({product.id}): {product.quantity} units @ ${product.price}")
    print()
    
    # Update quantity
    print("3. Updating quantities...")
    inventory.update_quantity("PROD002", -5)  # Sold 5 mice
    inventory.update_quantity("PROD001", 10)  # Restocked 10 laptops
    print("✓ Quantities updated\n")
    
    # Search products
    print("4. Searching for 'laptop':")
    results = inventory.search_products("laptop")
    for product in results:
        print(f"  - Found: {product.name} - {product.quantity} in stock")
    print()
    
    # Get low stock items
    print("5. Checking low stock items (threshold: 10):")
    low_stock = inventory.get_low_stock_products(10)
    for product in low_stock:
        print(f"  - {product.name}: {product.quantity} units remaining")
    print()
    
    # Get inventory summary
    print("6. Inventory Summary:")
    summary = inventory.get_inventory_summary()
    print(f"  Total Products: {summary['total_products']}")
    print(f"  Total Items: {summary['total_quantity']}")
    print(f"  Total Value: ${summary['total_value']:.2f}")
    print(f"  Categories: {', '.join(summary['categories_list'])}")
    print(f"  Low Stock Items: {summary['low_stock_items']}")
    print()
    
    # Category filtering
    print("7. Electronics category:")
    electronics = inventory.list_products("Electronics")
    for product in electronics:
        print(f"  - {product.name}: {product.quantity} @ ${product.price}")
    print()
    
    print("=== Demo Complete ===")


if __name__ == "__main__":
    demo()
