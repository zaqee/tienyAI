import requests

API = "http://127.0.0.1:8000/chat"

print("Basic Chat Demo (/chat)")
print("type 'exit' to quit\n")

while True:
    msg = input("You: ")

    if msg.lower() == "exit":
        break

    res = requests.post(API, json={"message": msg})

    if res.status_code != 200:
        print("Error:", res.text)
        continue

    print("AI:", res.json()["response"], "\n")