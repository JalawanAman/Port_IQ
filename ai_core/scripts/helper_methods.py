
import random
import re
import os
import json
from deep_translator import GoogleTranslator

def flatten_input_dict(input_dict, parent_key=''):
    parts = []
    for key, value in input_dict.items():
        full_key = f"{parent_key}.{key}" if parent_key else key
        if isinstance(value, dict):
            parts.append(flatten_input_dict(value, full_key))
        elif isinstance(value, list):
            list_values = ", ".join(str(item) for item in value)
            parts.append(f"{full_key}: [{list_values}]")
        else:
            parts.append(f"{full_key}: {value}")
    return ", ".join(parts)

def generate_random_eta( max_eta_str, current_eta_str='0h 35m', min_gap_minutes=95):
    try:
        # Helper function to convert ETA strings like "4h 1m" into total minutes
        def eta_to_minutes(eta_str):
            match = re.search(r'(\d+)h\s*(\d+)m', eta_str)
            if match:
                hours, minutes = map(int, match.groups())
                return hours * 60 + minutes
            raise ValueError(f"Invalid ETA format: {eta_str}")

        min_minutes = eta_to_minutes(current_eta_str)
        max_minutes = eta_to_minutes(max_eta_str)

        # Enforce the minimum gap constraint
        if (max_minutes - min_minutes) < min_gap_minutes:
            print(f"Insufficient range: Needs at least {min_gap_minutes} minutes gap between min and max ETA.")
            return current_eta_str

        # Generate ETA ≥ min_minutes and < max_minutes
        random_minutes = random.randint(min_minutes, max_minutes - 1)

        rand_hours = random_minutes // 60
        rand_minutes = random_minutes % 60

        return f"{rand_hours}h {rand_minutes}m"

    except Exception as e:
        print(f"Error generating random ETA: {e}")
        return current_eta_str  # Fallback to current ETA if an error occurs

def update_shipment_entry( updated_entry, tar_lang,  file_path="./ai_core/outputs/shipment_data.json"):
    try:
        
        updated_entry = trans_to_shipment_ar(updated_entry, tar_lang)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at {file_path}")

        with open(file_path, 'r') as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("Invalid JSON format: Root should be a list of shipment entries.")

        delivery_id = updated_entry.get("DeliveryID")
        if not delivery_id:
            raise ValueError("Updated entry must contain a 'DeliveryID' key.")

        # Search for the entry and update it
        for idx, entry in enumerate(data):
            if entry.get("DeliveryID") == delivery_id:
                data[idx] = updated_entry
                break
        else:
            # DeliveryID not found, optionally raise or append
            print(f"DeliveryID '{delivery_id}' not found. Adding as a new entry.")
            data.append(updated_entry)

        # Write back the updated data
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)

        print(f"Shipment with DeliveryID '{delivery_id}' has been updated successfully.")
        return True

    except Exception as e:
        print(f"Error updating shipment entry: {e}")
        return False




def get_translation(value: str, target_lang: str) -> str:

    translations = {
        # English to Arabic
        'Shuwaikh Port': 'ميناء شويخ',
        'Shuaiba Port': 'ميناء شعيبة ',
        'Doha Port': 'ميناء الدوحة',
        'Delayed': 'تأخير',
        'In Progress': 'في تَقَدم',
        'Pending': 'قيد الانتظار',
        
        # Arabic to English
        'ميناء شويخ': 'Shuwaikh Port',
        'ميناء شعيبة ':'Shuaiba Port',
        'ميناء الدوحة': 'Doha Port',
        'تأخير': 'Delayed',
        'في تَقَدم': 'In Progress',
        'قيد الانتظار': 'Pending',
    }

    # Simple function to check if a string is Arabic
    def is_arabic(text):
        return any('\u0600' <= char <= '\u06FF' for char in text)

    if target_lang == 'ar':
        if is_arabic(value):
            return value  # Already Arabic, return as is
        return translations.get(value, value)
    elif target_lang == 'en':
        if not is_arabic(value):
            return value  # Already English, return as is
        return translations.get(value, value)
    else:
        return f"Error: Unsupported language '{target_lang}'"


def to_ar(given, prefferd_lang='ar'):
    
    source = 'en'
    if prefferd_lang == 'en':
        source = 'ar'
    translated = GoogleTranslator(source=source, target=prefferd_lang).translate(given)
    return translated
    
def trans_to_shipment_ar(shipment_details, tar_lang):
    
    try:
        
        # shipment_details['Port'] = get_translation(shipment_details['Port'], tar_lang)
        # shipment_details['Status'] = get_translation(shipment_details['Status'], tar_lang)
        # print(shipment_details['Route']," : ",get_translation(shipment_details['Route'], tar_lang))
        # shipment_details['Route'] = get_translation(shipment_details['Route'], tar_lang)
        
        shipment_details['Port'] = to_ar(shipment_details['Port'], tar_lang)
        shipment_details['Status'] = to_ar(shipment_details['Status'], tar_lang)
        print(shipment_details['Route']," : ",to_ar(shipment_details['Route'], tar_lang))
        shipment_details['Route'] = to_ar(shipment_details['Route'], tar_lang)
        
        return shipment_details
    except Exception as e:
        raise e
    