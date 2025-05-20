from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

from ai_core.scripts.gen_response import generate_response_main, process_input, get_shipment_data
from ai_core.scripts.helper_methods import  generate_random_eta, update_shipment_entry, trans_to_shipment_ar, to_ar, get_translation
from django.conf import settings
from django.http import JsonResponse

def debug_allowed_hosts(request):
    return JsonResponse({'ALLOWED_HOSTS': settings.ALLOWED_HOSTS})

@csrf_exempt
@require_http_methods(["GET", "POST", "OPTIONS"])
def chat(request):
    try:
        print("\n----------------------------------------------------------------------------------------------\n\n")
        # Handle CORS Preflight Requests
        if request.method == "OPTIONS":
            response = JsonResponse({"status": "ok"})
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response["Access-Control-Allow-Headers"] = "*"
            return response

        if request.method == "GET":
            # Extract 'response' from query parameters
            response_param = request.GET.get('response')
            try:
                response_value = json.loads(response_param) if response_param else {}
                print("[GET] Parsed response:", response_value)
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON in query param.'}, status=400)
        else:  # POST request
            try:
                data = json.loads(request.body.decode('utf-8'))
                print("[POST] Received data:", data)
                response_value = data.get('response', {})
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)

        # Default dummy result
        
        print(f"response_value={response_value}, {type(response_value)}")
        
        pref_lang = response_value['lang']
        shipment_id = response_value['shipment_id']
        if shipment_id == False:
            shipment_id = None
        
        # Business logic based on 'user_input'
        if isinstance(response_value, dict) and response_value['user_input'] == False:
            # Process greeting and shipment suggestions
            input_gred, shipment_details, fuc, fuc_name, greet_role = process_input(details={"mode": "greeting", "Language": pref_lang}, shipment_id=shipment_id)
            input_shipment, shipment_details, fuc, fuc_name, sugg_role = process_input(details={"mode": "shipment_suggestion",  "Language": pref_lang}, shipment_id=shipment_id, gen_shipment_data=True)
            
            if not shipment_details:
               print("[Eror] Shipment details are empty!")
            
            
            notifications = {
                "shipment_status_updates": f"Container {shipment_details['Container']} has left port.",
                }

            
            if pref_lang == 'ar': 
                shipment_details = trans_to_shipment_ar(shipment_details, pref_lang)
            else:
                shipment_details =  get_shipment_data(rand_mode=False, shipment_id=shipment_id)
                
            if pref_lang == 'ar':
                notifications['shipment_status_updates'] = f" حاوية {shipment_details['Container']} قد غادر المنفذ"
                
            
            
            greet_res = generate_response_main(input_gred, fuc, fuc_name, greet_role)['message']
            suggestion_res = generate_response_main(input_shipment, fuc, fuc_name, sugg_role)
            
            result = {
                "delivery_details": shipment_details,
                "greeting": greet_res,
                "shipment_suggestion": suggestion_res,
                "notifications": notifications,
            }
            print("\n\n[Response Generated] (1st):", result)
            
        if isinstance(response_value, dict) and isinstance(response_value['user_input'], str):
            # Direct response based on user input
            # direct_response = generate_response_main(response_value)
            input_action, shipment_details, fuc, fuc_name, action_role = process_input(details={"mode": "action_response", "Language": pref_lang, "user_response": response_value['user_input'], "suggested_port": response_value['suggested_port']}, shipment_id= shipment_id )
            action_res_dict = generate_response_main(input_action, fuc, fuc_name, action_role)
            
            ActionAccepted = action_res_dict.get("ActionAccepted", False)
            status = action_res_dict.get("Status", "Pending")
            message = action_res_dict.get("message", "No message provided")
            
            
            if not response_value['suggested_port']:
                response_value['suggested_port'] = "Doha Port"
                if pref_lang: response_value['suggested_port'] = "ميناء الدوحة"
            
            
            

            if pref_lang == 'ar': 
                shipment_details = trans_to_shipment_ar(shipment_details, pref_lang)
            else:
                shipment_details = get_shipment_data(rand_mode=False, shipment_id=response_value['shipment_id'])
            
            
            
            
            if ActionAccepted:
                rerouted_alert = f"Delivery {shipment_details['DeliveryID']} has been rerouted to {response_value['suggested_port']} successfully."
                
            elif not ActionAccepted and status == "Completed":
                rerouted_alert = f"No rerouting action taken on delivery {shipment_details['DeliveryID']} continues on {shipment_details['Route']}."    
                
            else:
                rerouted_alert = False
            
            
            notifications = {
                "shipment_status_updates": f"Container {shipment_details['Container']} has left port.",
                "rerouted_alert": rerouted_alert,
                }
            
            if pref_lang == 'ar':
                notifications['shipment_status_updates'] = f" حاوية {shipment_details['Container']} قد غادر المنفذ"
                if rerouted_alert:
                    notifications['rerouted_alert'] = to_ar(rerouted_alert)
            

            updated_eta = generate_random_eta(shipment_details['ETA'])
            if ActionAccepted:
                # shipment_details['Route'] = get_translation(response_value['suggested_port'], pref_lang)
                print(response_value['suggested_port'])
                shipment_details['Route'] = response_value['suggested_port']
                shipment_details['ETA'] = updated_eta
                shipment_details['Status'] = 'في تَقَدم' if pref_lang == 'ar' else 'In Progress'
                print("SHIP: ", shipment_details)
            else:
                shipment_details= get_shipment_data(rand_mode=False, shipment_id=response_value['shipment_id'])
                if pref_lang == 'ar': shipment_details = trans_to_shipment_ar(shipment_details, pref_lang)
            
            
            # if pref_lang == 'ar': 
            #     shipment_details = trans_to_shipment_ar(shipment_details, pref_lang)
            # else:
            shipment_details = trans_to_shipment_ar(shipment_details, pref_lang)
            
            
            
            result = {
                "ActionAccepted": ActionAccepted,
                "Status": status,
                "message": message,
                "shipment_details": shipment_details,
                "notifications": notifications,
            }

            update_shipment_entry(shipment_details, 'en')
            print("\n\n[Generated Response] 2nd:", result)
            
        # Final response with CORS headers
        final_response = JsonResponse({'result': result}, status=200)
        final_response["Access-Control-Allow-Origin"] = "*"
        return final_response

    except Exception as e:
        print(f"[ERROR]: {str(e)}")
        error_response = JsonResponse({'error': f'Internal server error: {str(e)}'}, status=500)
        error_response["Access-Control-Allow-Origin"] = "*"
        # return error_response
        raise e