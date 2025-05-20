# Loading dependencies
import random
import openai
import json
import os
from datetime import datetime
import pytz
# from ai_core.scripts.helper_methods import flatten_input_dict
# from ai_core.scripts.prepare_conversation import get_conversation

from helper_methods import flatten_input_dict
from prepare_conversation import get_conversation
from data_prep_tuning import greet_sys_role, sugg_sys_role, action_sys_role

def get_api_key(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)["api_key"]
    else:
        raise FileNotFoundError(f"File not found at path: {file_path}")



def generate_response(client, messages, my_function, my_fuc_name, max_tokens=700, temperature=0.8):
    functions = my_function if isinstance(my_function, list) else [my_function]
    response = client.chat.completions.create(
        model="ft:gpt-3.5-turbo-1106:personal:nova-v2:BZEOZFby",
        # model="gpt-3.5-turbo",
        messages=messages,
        functions=functions,
        function_call=my_fuc_name,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=False
    )
    return response


# Sample ports


# Generate shipment data
def generate_port_shipment_data(file_path = "./ai_core/outputs/shipment_data.json"):
    try:
        shipments = []
        ports = ['Shuwaikh Port', 'Shuaiba Port', 'Doha Port']
        for i in range(500):
            port = random.choice(ports)
            shipment = {
                'DeliveryID': f'DEL-2025-{i+1:03}',
                'Port': port,
                'ETA': f"{random.randint(4, 5)}h {random.randint(0, 59)}m",
                'Status': random.choices(['Delayed', 'Pending'], weights=[0.5, 0.5])[0],
                'Impact': random.choice(['Port congestion', 'Severe weather forecast', 'Maintenance activity', 'Customs clearance delay', 'Limited container slots']),
                'Route': random.choice(ports),
                'RerouteOptions': random.sample([p for p in ports if p != port], 2)
            }
            shipments.append(shipment)
            
        # Save to JSON file
        with open(file_path, 'w') as f:
            json.dump(shipments, f, indent=4)
        
        return True
    except Exception as e:
        raise e
    
def get_shipment_data(file_path="./ai_core/outputs/shipment_data.json", rand_mode=True, shipment_id=None):
    # Load the JSON data from file
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in file {file_path}")
        return None
   
    # Return random shipment if rand_mode is True
    if rand_mode:
        return random.choice(data)

    # Else, return specific shipment by DeliveryID
    if shipment_id:
        for shipment in data:
            if shipment.get('DeliveryID') == shipment_id:
                return shipment
        print(f"Warning: No shipment found with DeliveryID {shipment_id}")
        return None

    # If neither rand_mode nor shipment_id is properly provided
    print("Error: rand_mode is False and no shipment_id was provided.")
    return None



def process_input(details, shipment_id, shipment_json_data_file = "./ai_core/outputs/shipment_data.json" , gen_shipment_data=False):
    
    
                
    f_call_greet = {
        "name": "greeting",
        "description": "Generates a time-of-day specific greeting for the user.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "A friendly, localized greeting message based on the current time and context."
                }
            },
            "required": ["message"]
        }
    }
    
    
    f_call_sugg = {
        "name": "shipment_suggestion",
        "description": "Provides a shipment status update with a suggested reroute port if applicable.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Shipment update message explaining the current status and recommendation."
                },
                "sugg_route": {
                    "type": "string",
                    "description": "Recommended port for rerouting the shipment."
                }
            },
            "required": ["message", "sugg_route"]
        }
    }

    f_call_action = {
        "name": "action_response",
        "description": "Confirms user response to a shipment reroute suggestion, including action status and final message.",
        "parameters": {
            "type": "object",
            "properties": {
                "ActionAccepted": {
                    "type": "boolean",
                    "description": "Whether the user accepted the suggested reroute."
                },
                "Status": {
                    "type": "string",
                    "enum": ["Pending", "Completed", "Failed"],
                    "description": "The current status of the shipment reroute decision."
                },
                "message": {
                    "type": "string",
                    "description": "Confirmation message detailing the final action taken or skipped. either false"
                },
                "sugg_route": {
                    "type": "string",
                    "description": "User overwritten, recommended port for rerouting the shipment"
                }
            },
            "required": ["ActionAccepted", "Status", "message", "sugg_route"]
        }
        
    }
    
    final_functions = {}
    
    
    if gen_shipment_data and not shipment_id:
        status = generate_port_shipment_data(shipment_json_data_file)
        if not status:
            return False
        
    mode = details.get("mode")
    lang = details.get("Language")
    input = {}
    shipment_details = {}
    cur_role = None
    
    if mode == 'greeting':
        cur_role = greet_sys_role
        kuwait_time_str = datetime.now(pytz.timezone('Asia/Kuwait')).strftime('%Y-%m-%d %H:%M:%S')
        input =  {
            # "mode": "Prod",
            "Language": lang,
            "context": "greeting",
            "conditions": {
                "time_of_day": kuwait_time_str
            }
        }
        final_functions = f_call_greet
        
    if mode == 'shipment_suggestion':
        cur_role = sugg_sys_role
        if shipment_id is None:
            shipment_details = get_shipment_data()
        else:    
            shipment_details = get_shipment_data(rand_mode=False, shipment_id=shipment_id)
            
        input =  {
            # "mode": "Prod",
            "Language": lang,
            "context": "shipment_suggestion",
            "conditions": shipment_details
        }
        final_functions = f_call_sugg
    
    if mode == 'action_response':
        
        cur_role = action_sys_role
        shipment_details = get_shipment_data(rand_mode=False, shipment_id=shipment_id)
        input =  {
            # "mode": "Prod",
            "Language": lang,
            "context": "action_response",
            "DateTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "suggested_route": details.get("suggested_port"),
            "conditions": shipment_details,
            "user_response": details.get("user_response")
        }
        final_functions = f_call_action
    
    return input, shipment_details, final_functions, {"name": mode}, cur_role
    
    
def generate_response_main(input, fuc, fuc_name, role, api_key_file = "./ai_core/inputs/gpt_api_key.json"):
    
    conversation = get_conversation()
    conversation = []
    # print(conversation)
    API_kEY = get_api_key(api_key_file)

    client = openai.OpenAI(api_key=API_kEY)

        
    # Add user input
    conversation.append({"role": "system", "content": role})
    conversation.append({"role": "user", "content": flatten_input_dict(input)})
    
    # Generate response
    res = generate_response(client, conversation, fuc, fuc_name)
    # print(res)
    # res_text = res.choices[0].message.content
    fuc_res = json.loads(res.choices[0].message.function_call.arguments)
    # conversation.append({"role": "assistant", "content": res_text})
    # return res
    return fuc_res


if __name__ == "__main__":
    try:
        key_file = "ai_core/inputs/gpt_api_key.json"
        ship_data_file = "ai_core/outputs/shipment_data.json"
        
        input_greet, ship_details, fuc, fuc_name, curr_role = process_input(details={"mode": "greeting"}, shipment_id=None, shipment_json_data_file=ship_data_file, gen_shipment_data=True)
        fuc_res = generate_response_main(input_greet, fuc, fuc_name, curr_role, api_key_file=key_file)
        print(fuc_res)
        input_thing, ship_details, fuc, fuc_name, curr_role = process_input(details={"mode": "shipment_suggestion"}, shipment_id=None, shipment_json_data_file=ship_data_file, gen_shipment_data=False)
        print(ship_details)
        fuc_res = generate_response_main(input_thing, fuc, fuc_name, curr_role,  api_key_file=key_file)
        print(fuc_res)
        
        input = "yes thats right."
        # input = "how are you buddyt."
        # input = "reroute it to Shuaiba route."
        input = "can you tell me a joke"
        
        id = ship_details["DeliveryID"]
        suggested = "Doha Port"
        suggested = fuc_res["sugg_route"]

        input_acc, ship_details, fuc, fuc_name, curr_role = process_input(details={"mode": "action_response", "user_response": input, "suggested_port": suggested}, shipment_id=id, shipment_json_data_file=ship_data_file, gen_shipment_data=False)
        fuc_res = generate_response_main(input_acc, fuc, fuc_name, curr_role, api_key_file=key_file)
        print(fuc_res)

    except Exception as e:
        raise e