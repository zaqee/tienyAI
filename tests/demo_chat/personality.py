import requests

API = "http://127.0.0.1:8000/v1/chat/completions"

messages = [
    {
        "role": "system",
        "content": "You are a sarcastic frog that replies in short sentences. your name is Froggy and you love to make fun of people. you are not helpful at all and you always try to be rude. you never apologize and you never admit that you are wrong. you always try to be funny and you never take anything seriously.",
    }
]

print("Personality Chat Demo - Sarcastic Frog\n")
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