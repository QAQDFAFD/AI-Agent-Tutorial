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
  const demo = location.hash.match(/^#\/demo\/([\w-]+)/);
  if (demo) return { kind: "demo", id: demo[1] };
  const chapter = location.hash.match(/^#\/chapter\/([\w.-]+)/);
  return { kind: "chapter", id: chapter ? chapter[1] : "00" };
}

function highlightCode(container) {
  if (!window.hljs) return;
  for (const block of container.querySelectorAll("pre code")) {
    hljs.highlightElement(block);
  }
}

async function renderPage(url, activeChapterId, anchor) {
  const response = await fetch(url);
  if (!response.ok) {
    chapterBody.innerHTML = "<p>页面不存在。</p>";
    return;
  }
  const page = await response.json();
  chapterBody.innerHTML = page.html;
  highlightCode(chapterBody);
  for (const link of chapterList.querySelectorAll("a")) {
    link.classList.toggle("active", link.dataset.chapterId === activeChapterId);
  }
  sidebar.classList.remove("open");
  const target = anchor && document.getElementById(anchor);
  (target || chapterBody).scrollIntoView({ block: "start" });
  if (!target) window.scrollTo({ top: 0 });
}

function renderChapter(chapterId, anchor) {
  return renderPage(`/api/chapters/${encodeURIComponent(chapterId)}`, chapterId, anchor);
}

function route() {
  const { kind, id } = currentRoute();
  if (kind === "demo") {
    renderPage(`/api/demos/${encodeURIComponent(id)}`, null);
  } else {
    renderChapter(id);
  }
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

/* ---------- 轻量 Markdown 渲染（先转义再渲染，防止模型输出注入 HTML） ---------- */

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderInline(text) {
  return text
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(
      /\[([^\]]+)\]\((https?:\/\/[^)\s]+|#[^)\s]*)\)/g,
      '<a href="$2" target="_blank" rel="noopener">$1</a>'
    );
}

function renderBlocks(text) {
  let html = "";
  let list = null;
  const closeList = () => {
    if (list) {
      html += `</${list}>`;
      list = null;
    }
  };
  for (const line of text.split("\n")) {
    const heading = line.match(/^#{1,6}\s+(.*)/);
    const bullet = line.match(/^\s*[-*]\s+(.*)/);
    const numbered = line.match(/^\s*\d+[.)]\s+(.*)/);
    const quote = line.match(/^&gt;\s?(.*)/);
    if (heading) {
      closeList();
      html += `<h4>${renderInline(heading[1])}</h4>`;
    } else if (quote) {
      closeList();
      html += `<blockquote>${renderInline(quote[1])}</blockquote>`;
    } else if (/^\s*(---+|\*\*\*+)\s*$/.test(line)) {
      closeList();
      html += "<hr>";
    } else if (bullet) {
      if (list !== "ul") { closeList(); html += "<ul>"; list = "ul"; }
      html += `<li>${renderInline(bullet[1])}</li>`;
    } else if (numbered) {
      if (list !== "ol") { closeList(); html += "<ol>"; list = "ol"; }
      html += `<li>${renderInline(numbered[1])}</li>`;
    } else if (line.trim() === "") {
      closeList();
    } else {
      closeList();
      html += `<p>${renderInline(line)}</p>`;
    }
  }
  closeList();
  return html;
}

function renderMarkdown(source) {
  // 偶数段是普通文本，奇数段是 ``` 围栏代码块（流式中未闭合的围栏也按代码块渲染）
  const parts = source.split("```");
  let html = "";
  for (let i = 0; i < parts.length; i++) {
    if (i % 2 === 1) {
      const code = parts[i].replace(/^[\w+-]*\n?/, "");
      html += `<pre><code>${escapeHtml(code)}</code></pre>`;
    } else {
      html += renderBlocks(escapeHtml(parts[i]));
    }
  }
  return html;
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
  let answerText = "";

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
        answerText += data.delta;
        answer.innerHTML = renderMarkdown(answerText);
        chatMessages.scrollTop = chatMessages.scrollHeight;
      } else if (event === "sources") {
        appendSources(data);
      } else if (event === "final") {
        // 流式期间不高亮（每个 token 都重建 DOM），结束后一次性高亮
        if (answer) highlightCode(answer);
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
