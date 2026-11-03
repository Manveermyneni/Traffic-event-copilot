from pathlib import Path
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_FILE = PROJECT_DIR / "data" / "uppal_stadium_event_traffic_data_pack.xlsx"

def load_data():
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_FILE}"
        )

    sheets = pd.read_excel(DATA_FILE, sheet_name=None)

    print("Available sheets:")
    for name, df in sheets.items():
        print(f"{name}: {df.shape[0]} rows, {df.shape[1]} columns")

    return sheets


if __name__ == "__main__":
    data = load_data()

    traffic = data["Traffic_Counts"]
    events = data["Events"]
    diversions = data["Diversions"]
    print("\n========== DIVERSION DATA INSPECTION ==========")

    print("\nColumn Names:")
    print(diversions.columns.tolist())

    print("\nDiversion Records:")
    print(diversions.to_string(index=False))

    print("\n========== DATASET SUMMARY ==========")

    for sheet_name, df in data.items():
        print(f"\nSheet: {sheet_name}")
        print("Rows:", len(df))
        print("Columns:", len(df.columns))
        print("Column names:")
        print(df.columns.tolist())

    print("\n========== TRAFFIC DATA ==========")

    print(traffic.describe(include="all").T)

    print("\n========== EVENT DETAILS ==========")
    print(events.to_string(index=False))

    print("\n========== DIVERSION DETAILS ==========")
    print(diversions.to_string(index=False))

    print("\nTraffic Counts Preview:")
    print(traffic.head())

    print("\nAvailable Events:")
    print(events[["Date", "Event_Name", "Day_Type"]].head())

    print("\nAvailable Diversions:")
    print(diversions.head())
