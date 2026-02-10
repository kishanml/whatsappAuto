import argparse
import datetime
import pandas as pd
from pathlib import Path
from whatsappAuto import whatsappAuto
from main import generate_classification

async def main():
    parser = argparse.ArgumentParser(description="WhatsApp Chat Monitor & Merger")
    parser.add_argument("--group", type=str, required=True, help="Name of the WhatsApp group")
    parser.add_argument("--merge", action="store_true", help="Merge new data into existing history")
    args = parser.parse_args()

    group_name = args.group
    database_dir = Path("database")
    database_dir.mkdir(parents=True, exist_ok=True)
    history_file = database_dir / f"{group_name}.xlsx"


    if args.merge and history_file.exists():
        existing_df = pd.read_excel(history_file)
        last_entry = f"{existing_df['date'].iloc[-1]} {existing_df['time'].iloc[-1]}"
        last_updated_date = pd.to_datetime(last_entry, dayfirst=True)
        print(f"Merging enabled. Last record found: {last_updated_date}")
    else:
        last_updated_date = pd.to_datetime(datetime.datetime.today().date())
        existing_df = pd.DataFrame()
        print(f"Fresh export. Fetching chats from: {last_updated_date}")

    wa = whatsappAuto()
    updated_data = wa.get_chats(group_name, last_updated_date)

    if not updated_data.empty:
        print(f"Found {len(updated_data)} new messages. Classifying...")
        
        is_concerns = await generate_classification(updated_data['message'].values)
        updated_data['is_concern'] = is_concerns

        if args.merge and not existing_df.empty:
            final_df = pd.concat([existing_df, updated_data], ignore_index=True)
            final_df = final_df.drop_duplicates(subset=['date', 'time', 'message'], keep='first')
        else:
            final_df = updated_data

        final_df.to_excel(history_file, index=False)
        print(f"Successfully saved to {history_file}")
    else:
        print("No new messages found since last update.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())