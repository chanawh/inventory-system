import sqlite3
import os

# Determine the absolute path to orders.db in the src directory
db_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'orders.db')
db_path = os.path.abspath(db_path)

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Print all table names
print("Tables:")
for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table';"):
    print(row)

# Print all orders
print("\nOrder Table:")
for row in cursor.execute("SELECT * FROM orders;"):
    print(row)

# Print all order items
print("\nOrder Items Table:")
for row in cursor.execute("SELECT * FROM order_items;"):
    print(row)

# Close the connection
conn.close()