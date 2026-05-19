function getSource() {
  const host = location.hostname;
  if (host.includes("gemini.google.com")) return "gemini";
  return "chatgpt";
}

function extractChatGPT() {
  const turns = document.querySelectorAll("[data-message-author-role]");
  let text = "";
  turns.forEach(el => {
    const role = el.getAttribute("data-message-author-role");
    const label = role === "user" ? "**나**" : "**AI**";
    text += `${label}:\n${el.innerText.trim()}\n\n`;
  });
  const titleEl = document.querySelector("title");
  return {
    title: titleEl ? titleEl.innerText.replace(" - ChatGPT", "").trim() : "ChatGPT 대화",
    content: text,
  };
}

function extractGemini() {
  const turns = document.querySelectorAll("message-content, user-query");
  let text = "";
  turns.forEach(el => {
    const isUser = el.tagName.toLowerCase() === "user-query";
    const label = isUser ? "**나**" : "**AI**";
    text += `${label}:\n${el.innerText.trim()}\n\n`;
  });
  return {
    title: document.title.replace(" - Gemini", "").trim() || "Gemini 대화",
    content: text,
  };
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.action !== "save") return;

  const source = getSource();
  const { title, content } = source === "gemini" ? extractGemini() : extractChatGPT();

  if (!content.trim()) {
    sendResponse({ status: "empty" });
    return;
  }

  fetch("http://localhost:8765/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source, title, content }),
  })
    .then(r => r.json())
    .then(data => sendResponse(data))
    .catch(err => sendResponse({ status: "error", error: err.message }));

  return true;
});
