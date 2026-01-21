
import json
import os

with open("local_applications.json", "r") as f:
    data = json.load(f)

for app in data:
    bank = app.get('selected_bank')
    print(f"Name: {app.get('input', {}).get('Name')}, Bank: '{bank}', Repr: {repr(bank)}")
