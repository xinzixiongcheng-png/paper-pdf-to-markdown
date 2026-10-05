# 直接打开本地网页

1. 双击 `start_web.bat` 启动本地 MarkItDown 服务。
2. 然后双击根目录的 `index.html`。
3. 页面可以拖入多个 PDF，批量转换后下载 ZIP。
4. ZIP 会按论文分目录保存 `.md` 和 `images/`，Markdown 使用相对路径。

也可以直接访问 `http://127.0.0.1:8765`，效果相同。

> 注意：`index.html` 是完整前端文件，但 PDF → Markdown 的转换仍由本机 Python/MarkItDown 服务完成；纯 HTML 在浏览器沙箱中不能直接运行 Python MarkItDown。
