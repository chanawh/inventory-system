import sqlite3
import pandas as pd
from pathlib import Path

# Get the absolute path to the directory containing this script.
script_directory = Path(__file__).parent.absolute()
DATABASE = script_directory.parent / "inventory.db"

def print_table(df):
    print("\nInventory Table:")
    print(df.to_string(index=False))

def print_ascii_bar_chart(series):
    print("\nInventory by Location (ASCII Bar Chart):")
    max_label = max(len(str(label)) for label in series.index)
    max_qty = series.max()
    scale = 50 / max_qty if max_qty > 0 else 1
    for loc, qty in series.items():
        bar = "#" * int(qty * scale)
        print(f"{loc.ljust(max_label)} | {bar} ({qty})")

def visualize_inventory():
    """Fetches data from the database and prints inventory as a table and ASCII bar chart."""
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

        print_table(df)

        # Group the data by location and sum the quantities
        inventory_by_location = df.groupby("location")["quantity"].sum()

        print_ascii_bar_chart(inventory_by_location)

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    visualize_inventory()