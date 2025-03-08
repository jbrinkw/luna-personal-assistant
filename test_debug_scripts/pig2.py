from db_functions import run_query, get_daily_notes_range

# Verify updates using get_daily_notes_range
results = get_daily_notes_range('2025-01-01', '2025-01-07')
print("\nUpdated Notes for First Week of 2025:")
print("=====================================")
for date, day, notes in results:
    print(f"\n{date} ({day}):")
    print(f"  {notes}")