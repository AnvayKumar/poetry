import requests

APP_ID = "1657540198722753"
APP_SECRET = "3eb3100d8438becab248a1284c59a8fa"
SHORT_LIVED_TOKEN = "EAAXjhiaZB7MEBRXrEIdeHGLuml4WtCxCh6Vdc9ZAUXxwlZAZCWYreqmOatb3aeqzJZCqHZCBYTTIwZCJtyhlUnoRMZAEYCf9nUgrRNJzjAv5833LNJHM7eOb3JOKZAfZBb7elu8ZCR2wGY08Arr7vZAeKOjjS2GCVdPbqZCFdhdfDRr6i4d6PXIwNsjEu7FzM7pWFxIfYFcU7wYPZCSZBBkSyrutZAnrIpG5530olvC5gITBzNcR"

def get_long_lived_token():
    url = "https://graph.facebook.com/v18.0/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "fb_exchange_token": SHORT_LIVED_TOKEN
    }
    
    response = requests.get(url, params=params)
    result = response.json()
    
    if "access_token" in result:
        print("\n✅ Long-lived token generated!")
        print("\nYour long-lived token (save this):")
        print(result["access_token"])
        print("\nExpires in: ~60 days")
    else:
        print(f"Error: {result}")

if __name__ == "__main__":
    get_long_lived_token()