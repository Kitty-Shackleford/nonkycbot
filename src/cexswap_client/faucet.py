"""Auto Claim CEXSwap Faucet"""
import keyring
from playwright.sync_api import sync_playwright
import requests
import json
import os

# Save credentials securely to keyring
def save_credentials(service, username, password):
    print(f"Saving credentials for {username}...")
    keyring.set_password(service, username, password)
    print(f"Credentials saved successfully for {username}!")

# Save username in keyring (so you don't have to enter it again)
def save_username(service, username):
    keyring.set_password(service, "saved_username", username)
    print(f"Username '{username}' saved in keyring.")

# Retrieve credentials from keyring
def load_credentials(service, username):
    print(f"Loading credentials for {username}...")
    password = keyring.get_password(service, username)
    if password:
        print(f"Credentials found for {username}.")
        return password
    else:
        print(f"No credentials found for {username}.")
        return None

# Retrieve saved username from keyring
def load_username(service):
    username = keyring.get_password(service, "saved_username")
    if username:
        print(f"Found saved username: {username}")
    return username

# Function to get tokens from JavaScript storage
def get_js_tokens(page):
    js_code = """
    (function() {
        var tokens = {};
        if (window.localStorage) {
            tokens.localStorage = window.localStorage;
        }
        if (window.sessionStorage) {
            tokens.sessionStorage = window.sessionStorage;
        }
        return tokens;
    })();
    """
    tokens = page.evaluate(js_code)
    #print(f"Local Storage and Session Storage Tokens: {tokens}")
    return tokens


# Create the 'data' directory if it doesn't exist
if not os.path.exists('data'):
    os.makedirs('data')

# Function to pretty-print the faucet list response
def print_faucet_list(response_json, filename="data/faucet_list.json"):
    if "items" in response_json:
        faucet_data = []
        print(f"{'Coin':<10} {'Per Claim':<25} {'Remaining':<25} {'Next Claim Time':<25} {'Can Claim'}")
        print("="*100)
        for item in response_json["items"]:
            coin = item["coin"]
            per_claim = item["per_claim"]
            remaining = item["remaining"]
            next_claim = item["next"]
            can_claim = "Yes" if item["can_claim"] else "No"
            
            # Print to console for user
            print(f"{coin:<10} {per_claim:<25} {remaining:<25} {next_claim:<25} {can_claim}")
            
            # Save item to list for future use
            faucet_data.append({
                "coin": coin,
                "per_claim": per_claim,
                "remaining": remaining,
                "next_claim": next_claim,
                "can_claim": item["can_claim"]
            })

        # Save the faucet data to a JSON file
        with open(filename, "w") as file:
            json.dump(faucet_data, file, indent=4)

        print(f"Faucet list saved to {filename}")
    else:
        print("No 'items' found in the response.")

# Main logic to dump cookies and tokens (headers if needed)
def dump_cookies(username=None, password=None):
    service_name = "cexswap"

    # Attempt to load saved username if none provided
    if username is None:
        username = load_username(service_name)
        if username is None:
            username = input("Enter username: ")
    
    # Attempt to load the password from the keyring based on the provided username
    password = load_credentials(service_name, username)

    if password is None:
        print("No saved credentials found. Please enter your password.")
        password = input("Enter password: ")
        save_credentials(service_name, username, password)  # Save credentials securely
    else:
        print(f"Using saved credentials for {username}.")

    # Save the username for future runs
    save_username(service_name, username)

    with sync_playwright() as p:
        print("Launching browser...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Log requests/responses for debugging
        def log_request(request):
            print(f"Request: {request.method} {request.url}")
            print(f"Request Headers: {request.headers}")

        def log_response(response):
            #print(f"Response: {response.status} {response.url}")
            if response.status == 200:
                try:
                    if 'application/json' in response.headers.get('content-type', ''):
                        response_json = response.json()
                        if "api/faucet/list" in response.url:
                            print("Faucet List Response:")
                            print_faucet_list(response_json)
                except Exception as e:
                    print(f"Error parsing response JSON: {e}")

        page.on("route", log_request)
        page.on("response", log_response)

        print("Navigating to login page...")
        page.goto("https://cexswap.cc/login")

        print("Filling in the login form...")
        page.fill('input[placeholder="Email or username"]', username)
        page.fill('input[placeholder="Password"]', password)
        page.click('button[type="submit"]')
        print("Form submitted. Waiting for page to load...")

        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(5000)

        print("Navigating to claim page...")
        page.goto("https://cexswap.cc/claim")
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(5000)

        #print("Extracting cookies...")
        cookies = page.context.cookies()
        jwt_token = None
        xsrf_token = None

        for cookie in cookies:
            if cookie['name'] == 'Authorization':
                jwt_token = cookie['value']
                #print(f"Authorization token in cookies: {jwt_token}")
            if cookie['name'] == 'XSRF-TOKEN':
                xsrf_token = cookie['value']
                #print(f"X-XSRF-TOKEN in cookies: {xsrf_token}")

        if not jwt_token or not xsrf_token:
            #print("No relevant tokens found in cookies. Checking JavaScript storage...")
            tokens = get_js_tokens(page)
            if 'localStorage' in tokens and 'cex_auth_v1' in tokens['localStorage']:
                # Parse the JWT string in localStorage
                jwt_data = json.loads(tokens['localStorage']['cex_auth_v1'])
                jwt_token = jwt_data.get("token")  # Extract the actual JWT token
                #print(f"JWT token in localStorage: {jwt_token}")
            if 'sessionStorage' in tokens:
                session_tokens = tokens['sessionStorage']
                if 'X-XSRF-TOKEN' in session_tokens:
                    xsrf_token = session_tokens['X-XSRF-TOKEN']
                    #print(f"X-XSRF-TOKEN in sessionStorage: {xsrf_token}")

        #print(f"Final JWT Token: {jwt_token}")
        #print(f"Final XSRF Token: {xsrf_token}")

        # Proceed with claiming coins once
        print("Checking faucet list...")
        response = requests.get(
            'https://cexswap.cc/api/faucet/list',
            headers = {
                "Authorization": f"Bearer {jwt_token}",
                "X-CSRF-Token": xsrf_token,
                "X-XSRF-TOKEN": xsrf_token,
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": "https://cexswap.cc/claim",
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0",
                "Cookie": f"XSRF-TOKEN={xsrf_token}",
            }
        )
        
        if response.status_code == 200:
            response_json = response.json()
            for item in response_json["items"]:
                if item["can_claim"]:
                    print(f"Coin '{item['coin']}' is available to claim!")
                    # Trigger claim (customize based on the actual endpoint and action)
                    claim_url = f'https://cexswap.cc/api/faucet/claim?item_id={item["id"]}'
                    claim_response = requests.post(claim_url, headers={
                        'Authorization': f'Bearer {jwt_token}',
                        'X-CSRF-Token': xsrf_token
                    })
                    if claim_response.status_code == 200:
                        print(f"Claimed {item['coin']} successfully!")
                    else:
                        print(f"Failed to claim {item['coin']}. Status code: {claim_response.status_code}")
        else:
            print(f"Error checking faucet list: {response.status_code}")

        # Close the browser after the single check and claim attempt
        print(f"No coins left to claim!")
        browser.close()

# Usage Example:
dump_cookies()  # Will automatically use saved username/password if available
