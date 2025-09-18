import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Get the absolute path to the directory containing this script.
# `Path(__file__).parent` gets the script's directory.
# `.parent` again moves up one level to the parent directory.
script_directory = Path(__file__).parent.absolute()
DATABASE = script_directory.parent / "inventory.db"

def visualize_inventory():
    """Fetches data from the database and creates a bar chart."""
    try:
        # Check if the database file exists
        if not Path(DATABASE).exists():
            print(f"Error: Database file not found at {DATABASE}")
            return
            
        conn = sqlite3.connect(DATABASE)

        # Read the entire 'inventory' table into a pandas DataFrame
        df = pd.read_sql_query("SELECT * FROM inventory", conn)

        # Close the database connection
        conn.close()

        # Check if the DataFrame is empty
        if df.empty:
            print("The inventory table is empty. Please insert data first.")
            return

        # Group the data by location and sum the quantities
        inventory_by_location = df.groupby("location")["quantity"].sum()

        # Create a bar chart
        plt.figure(figsize=(10, 6))
        inventory_by_location.plot(kind="bar", color="skyblue")
        plt.title("Total Inventory by Location")
        plt.xlabel("Location")
        plt.ylabel("Total Quantity")
        plt.xticks(rotation=45, ha="right") # Rotate labels for better readability
        plt.tight_layout() # Adjust plot to ensure everything fits
        plt.show()

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    visualize_inventory()
