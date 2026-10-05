# MarkItDown 本地论文批处理网页

启动后打开 `http://127.0.0.1:8765`。

## 功能

- 一次拖入或选择多个 PDF。
- MarkItDown 负责正文和可识别表格的 Markdown 转换。
- PyMuPDF 提取 PDF 中的嵌入式栅格图片。
- 每篇论文独立目录：

```text
论文名/
├── 论文名.md
└── images/
    ├── image_001.png
    └── image_002.jpg
```

Markdown 中使用 `images/image_001.png` 等相对路径，因此整个论文目录移动到其他位置后图片引用仍然有效。

批量转换后会下载一个 ZIP，内含所有论文目录；失败的文件会记录在 `转换失败记录.txt`。

## 注意

MarkItDown 当前 PDF 转换器会将可识别的表格尽可能转换为 Markdown 表格。图片的提取与 Markdown 链接是本地网页额外完成的；对于复杂 PDF，图片在 Markdown 中会集中放在文末的“图片”章节，而不是保证完全恢复原 PDF 中的版面位置。
