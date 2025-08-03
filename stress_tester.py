import requests
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

url = "http://192.168.0.38:7860/api/v1/run/4b64410c-ffa2-4782-803c-d3cc810a32d9"
# The complete API endpoint URL for this flow

# Configuration - Change this to control number of concurrent requests
NUM_CONCURRENT_REQUESTS = 75

def make_request(request_id):
    """Make a single API request and return the response with timing"""
    start_time = time.time()
    
    # Request payload configuration
    payload = {
        "input_value": f"hello world! (request {request_id})",  # The input value to be processed by the flow
        "output_type": "chat",  # Specifies the expected output format
        "input_type": "chat",  # Specifies the input format
        "tweaks": {
            "ChatInput-3Z3av": {
                "files": []
            }
        }  # Custom tweaks to modify flow behavior
    }

    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        
        # Parse the JSON response
        json_response = response.json()
        
        # Extract the message reply from the agent
        if 'outputs' in json_response and len(json_response['outputs']) > 0:
            outputs = json_response['outputs'][0]['outputs']
            if len(outputs) > 0:
                # Get the message from the first output
                message_data = outputs[0].get('results', {}).get('message', {})
                if 'text' in message_data:
                    agent_reply = message_data['text']
                    end_time = time.time()
                    duration = end_time - start_time
                    return f"Request {request_id}: {agent_reply} (took {duration:.2f}s)"
                else:
                    end_time = time.time()
                    duration = end_time - start_time
                    return f"Request {request_id}: No text found in response (took {duration:.2f}s)"
            else:
                end_time = time.time()
                duration = end_time - start_time
                return f"Request {request_id}: No outputs found in response (took {duration:.2f}s)"
        else:
            end_time = time.time()
            duration = end_time - start_time
            return f"Request {request_id}: Invalid response format (took {duration:.2f}s)"
        
    except requests.exceptions.RequestException as e:
        end_time = time.time()
        duration = end_time - start_time
        return f"Request {request_id}: Error making request - {e} (took {duration:.2f}s)"
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        return f"Request {request_id}: Unexpected error - {e} (took {duration:.2f}s)"

# Send concurrent requests
print(f"Sending {NUM_CONCURRENT_REQUESTS} concurrent requests...")
start_time = time.time()

with ThreadPoolExecutor(max_workers=NUM_CONCURRENT_REQUESTS) as executor:
    # Submit all requests
    future_to_request = {executor.submit(make_request, i): i for i in range(1, NUM_CONCURRENT_REQUESTS + 1)}
    
    # Collect results as they complete
    results = []
    for future in as_completed(future_to_request):
        result = future.result()
        results.append(result)
        print(result)

end_time = time.time()
total_duration = end_time - start_time
print(f"\nAll requests completed in {total_duration:.2f} seconds")
print(f"Successfully processed {len(results)} requests")
print(f"Average time per request: {total_duration/len(results):.2f} seconds") 