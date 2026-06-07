import getpass
import requests

base_url = "https://campaigns.healthyw8.gamebus.eu".rstrip("/")

email = input("Email: ").strip()
password = getpass.getpass("Password: ")

if not email:
    raise RuntimeError("Email is empty.")
if not password:
    raise RuntimeError("Password is empty.")

session = requests.Session()
session.headers.update({
    "User-Agent": "GameBus-Campaign-Assistant-Diagnostic/1.0"
})

print("\nTrying login...")
response = session.post(
    f"{base_url}/api/auth/token",
    json={
        "email": email,
        "password": password,
    },
    timeout=30,
)

headers_lower = {k.lower(): v for k, v in response.headers.items()}

print("Status:", response.status_code)
print("Content-Type:", response.headers.get("Content-Type"))
print("Set-Cookie present:", "set-cookie" in headers_lower)
print("Cookies after login:", session.cookies.get_dict())

text = response.text or ""
print("Response preview:")
print(text[:500])

if response.status_code == 200:
    if "__session" in session.cookies.get_dict():
        print("\nLogin OK: __session cookie was set.")
    else:
        print("\nLogin returned 200 but no __session cookie was set.")
else:
    print("\nLogin failed before campaign download.")
