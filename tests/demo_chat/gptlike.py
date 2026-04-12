import requests

API = "http://127.0.0.1:8000/v1/chat/completions"

messages = []

print("ChatGPT-style Demo")
print("type 'exit' to quit\n")

while True:
    msg = input("You: ")

    if msg.lower() == "exit":
        break

    messages.append({"role": "user", "content": msg})

    res = requests.post(API, json={"messages": messages})

    if res.status_code != 200:
        print("Error:", res.text)
        continue

    reply = res.json()["choices"][0]["message"]["content"]

    print("AI:", reply, "\n")

    messages.append({"role": "assistant", "content": reply})