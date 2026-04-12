const API = "http://127.0.0.1:8000/v1/chat/completions";

let messages = [];

async function send() {
  const input = document.getElementById("input");
  const text = input.value;

  if (!text) return;

  addMsg("You", text, "user");

  messages.push({ role: "user", content: text });

  input.value = "";

  const res = await fetch(API, {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ messages })
  });

  const data = await res.json();

  const reply = data.choices[0].message.content;

  addMsg("AI", reply, "ai");

  messages.push({ role: "assistant", content: reply });
}

function addMsg(name, text, cls) {
  const chat = document.getElementById("chat");

  const div = document.createElement("div");
  div.className = "msg " + cls;
  div.textContent = `${name}: ${text}`;

  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}