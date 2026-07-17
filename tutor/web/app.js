/* 教程阅读器 + 教学助手聊天组件（原生 JS，无构建工具） */

const chapterList = document.getElementById("chapter-list");
const chapterBody = document.getElementById("chapter-body");
const sidebar = document.getElementById("sidebar");

// ---------- 阅读器 ----------

async function loadChapters() {
  const response = await fetch("/api/chapters");
  const chapters = await response.json();
  chapterList.innerHTML = "";
  for (const chapter of chapters) {
    const item = document.createElement("li");
    const link = document.createElement("a");
    link.href = `#/chapter/${chapter.id}`;
    link.textContent = chapter.title;
    link.dataset.chapterId = chapter.id;
    item.appendChild(link);
    chapterList.appendChild(item);
  }
}

function currentRoute() {
  const match = location.hash.match(/^#\/chapter\/([\w.-]+)/);
  return match ? match[1] : "00";
}

async function renderChapter(chapterId, anchor) {
  const response = await fetch(`/api/chapters/${encodeURIComponent(chapterId)}`);
  if (!response.ok) {
    chapterBody.innerHTML = "<p>章节不存在。</p>";
    return;
  }
  const chapter = await response.json();
  chapterBody.innerHTML = chapter.html;
  for (const link of chapterList.querySelectorAll("a")) {
    link.classList.toggle("active", link.dataset.chapterId === chapterId);
  }
  sidebar.classList.remove("open");
  const target = anchor && document.getElementById(anchor);
  (target || chapterBody).scrollIntoView({ block: "start" });
  if (!target) window.scrollTo({ top: 0 });
}

function route() {
  renderChapter(currentRoute());
}

window.addEventListener("hashchange", route);

document.getElementById("sidebar-toggle").addEventListener("click", () => {
  sidebar.classList.toggle("open");
});

// ---------- 聊天助手 ----------

const chatPanel = document.getElementById("chat-panel");
const chatMessages = document.getElementById("chat-messages");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatSend = document.getElementById("chat-send");

document.getElementById("chat-toggle").addEventListener("click", () => {
  chatPanel.classList.toggle("hidden");
  if (!chatPanel.classList.contains("hidden")) chatInput.focus();
});
document.getElementById("chat-close").addEventListener("click", () => {
  chatPanel.classList.add("hidden");
});

function threadId() {
  let id = localStorage.getItem("tutor-thread");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("tutor-thread", id);
  }
  return id;
}

function appendMessage(className, text) {
  const element = document.createElement("div");
  element.className = `msg ${className}`;
  element.textContent = text;
  chatMessages.appendChild(element);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return element;
}

function appendSources(sources) {
  const wrap = document.createElement("div");
  wrap.className = "sources";
  for (const source of sources) {
    const chip = document.createElement("button");
    chip.className = "source-chip";
    chip.textContent = `第 ${source.chapter_id} 章 · ${source.heading}`;
    chip.addEventListener("click", () => {
      location.hash = `#/chapter/${source.chapter_id}`;
      renderChapter(source.chapter_id, source.anchor);
    });
    wrap.appendChild(chip);
  }
  chatMessages.appendChild(wrap);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function disableChat(reason) {
  chatInput.disabled = true;
  chatSend.disabled = true;
  chatInput.placeholder = reason;
}

async function checkHealth() {
  try {
    const health = await (await fetch("/api/health")).json();
    if (!health.chat_enabled) {
      disableChat("聊天未启用：请配置 OPENAI_API_KEY 后重启服务（见附录 A）");
    }
  } catch {
    disableChat("无法连接服务");
  }
}

/* 手工解析 SSE：按空行分帧，每帧含 event: 与 data: 两行 */
function parseSSE(buffer, onEvent) {
  const frames = buffer.split("\n\n");
  const rest = frames.pop(); // 最后一段可能不完整，留到下一轮
  for (const frame of frames) {
    let event = "message";
    let data = "";
    for (const line of frame.split("\n")) {
      if (line.startsWith("event: ")) event = line.slice(7);
      if (line.startsWith("data: ")) data = line.slice(6);
    }
    if (data) onEvent(event, JSON.parse(data));
  }
  return rest;
}

async function sendMessage(text) {
  appendMessage("user", text);
  const status = appendMessage("status", "思考中…");
  let answer = null;

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ thread_id: threadId(), message: text }),
    });

    if (response.status === 503) {
      const detail = (await response.json()).detail;
      status.remove();
      appendMessage("error", detail);
      disableChat("聊天未启用：请配置 OPENAI_API_KEY（见附录 A）");
      return;
    }
    if (!response.ok) {
      status.remove();
      appendMessage("error", "请求失败，请稍后重试。");
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    const onEvent = (event, data) => {
      if (event === "tool_call") {
        status.textContent =
          data.tool === "search_tutorial" ? "正在查阅教程…" : "正在整理章节目录…";
      } else if (event === "token") {
        if (!answer) answer = appendMessage("assistant", "");
        answer.textContent += data.delta;
        chatMessages.scrollTop = chatMessages.scrollHeight;
      } else if (event === "sources") {
        appendSources(data);
      } else if (event === "error") {
        appendMessage("error", data.message);
      }
    };

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      buffer = parseSSE(buffer, onEvent);
    }
  } catch {
    appendMessage("error", "网络错误，请稍后重试。");
  } finally {
    status.remove();
  }
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = chatInput.value.trim();
  if (!text || chatSend.disabled) return;
  chatInput.value = "";
  chatSend.disabled = true;
  try {
    await sendMessage(text);
  } finally {
    chatSend.disabled = chatInput.disabled; // 聊天被禁用时保持禁用
    chatInput.focus();
  }
});

// ---------- 启动 ----------

loadChapters().then(route);
checkHealth();
