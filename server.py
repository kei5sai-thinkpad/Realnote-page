from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

html = r"""
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>NoteCord - Code Style</title>

<style>
body {
    margin: 0;
    font-family: sans-serif;
    background: #0f172a;
    color: white;
    display: flex;
    height: 100vh;
}

/* 左側 */
.sidebar {
    width: 320px;
    background: #020617;
    padding: 20px;
    border-right: 1px solid #1e293b;
    box-sizing: border-box;
}

.sidebar h2 {
    margin-top: 0;
}

/* 右側 */
.main {
    flex: 1;
    display: flex;
    flex-direction: column;
}

.header {
    padding: 18px 24px;
    background: #020617;
    border-bottom: 1px solid #1e293b;
    font-size: 18px;
    font-weight: bold;
}

/* 入力欄 */
textarea {
    width: 100%;
    height: 220px;
    background: #111827;
    color: white;
    border: none;
    border-radius: 14px;
    padding: 16px;
    font-size: 14px;
    resize: none;
    outline: none;
    box-sizing: border-box;
    line-height: 1.6;
}

/* プレビュー */
#note {
    flex: 1;
    padding: 24px;
    overflow: auto;
    line-height: 1.8;
    white-space: pre-wrap;
}

/* コードブロック */
.code-block {
    background: #111827;
    border: 1px solid #334155;
    border-radius: 16px;
    margin: 18px 0;
    overflow: hidden;
}

.code-top {
    background: #0b1220;
    padding: 12px 16px;
    border-bottom: 1px solid #334155;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.code-label {
    font-size: 14px;
    font-weight: bold;
    color: #cbd5e1;
}

.copy-btn {
    background: transparent;
    border: 1px solid #475569;
    color: #cbd5e1;
    padding: 6px 12px;
    border-radius: 10px;
    cursor: pointer;
    font-size: 13px;
}

.copy-btn:hover {
    background: #1e293b;
}

.code-content {
    padding: 18px;
    font-family: Consolas, monospace;
    font-size: 14px;
    line-height: 1.7;
    white-space: pre-wrap;
    overflow-x: auto;
}
</style>
</head>
<body>

<div class="sidebar">
    <h2>入力欄</h2>

    <textarea id="editor" placeholder="ここに入力してください"></textarea>
</div>

<div class="main">
    <div class="header">
        ChatGPT風 コード自動認識
    </div>

    <div id="note"></div>
</div>

<script>
const editor = document.getElementById("editor");
const note = document.getElementById("note");

/* HTMLエスケープ */
function escapeHtml(text) {
    const div = document.createElement("div");
    div.innerText = text;
    return div.innerHTML;
}

/* コピー */
function copyCode(button) {
    const code = button.parentElement.nextElementSibling.innerText;

    navigator.clipboard.writeText(code);

    button.innerText = "コピー完了";

    setTimeout(() => {
        button.innerText = "コピー";
    }, 1500);
}

/* コードブロック変換 */
function formatCodeBlocks(text) {
    return text.replace(
        /```(\w+)?\n([\s\S]*?)```/g,
        function(match, lang, code) {
            return `
                <div class="code-block">
                    <div class="code-top">
                        <div class="code-label">
                            ${lang || "code"}
                        </div>

                        <button
                            class="copy-btn"
                            onclick="copyCode(this)"
                        >
                            コピー
                        </button>
                    </div>

                    <div class="code-content">
${escapeHtml(code)}
                    </div>
                </div>
            `;
        }
    );
}

/* リアルタイム反映 */
function updatePreview() {
    const rawText = editor.value;
    note.innerHTML = formatCodeBlocks(rawText);
}

editor.addEventListener("input", updatePreview);

/* 初期テキスト */
editor.value =
`これは普通の文章です。

\`\`\`python
print("Hello World")

for i in range(5):
    print(i)
\`\`\`

ここはまた普通の文章です。

\`\`\`javascript
console.log("JavaScript")
\`\`\`
`;

updatePreview();
</script>

</body>
</html>
"""

@app.get("/")
async def home():
    return HTMLResponse(html)
