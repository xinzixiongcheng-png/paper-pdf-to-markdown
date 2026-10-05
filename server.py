#!/usr/bin/env python3
"""Web UI for batch converting PDFs to Markdown with images preserved."""
from __future__ import annotations

import argparse
import io
import json
import re
import tempfile
import zipfile
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, urlparse

from markitdown import MarkItDown

try:
    import fitz  # PyMuPDF
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("缺少 PyMuPDF，请重新运行启动脚本安装依赖。") from exc

MAX_FILE = 200 * 1024 * 1024
MAX_TOTAL = 500 * 1024 * 1024
MAX_FILES = 100
ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"


def parse_multipart(content_type: str, body: bytes) -> list[tuple[bytes, str]]:
    msg = BytesParser(policy=default).parsebytes(
        b"Content-Type: " + content_type.encode() + b"\r\n"
        b"MIME-Version: 1.0\r\n\r\n" + body
    )
    if not msg.is_multipart():
        raise ValueError("请求不是 multipart/form-data")

    files: list[tuple[bytes, str]] = []
    for part in msg.iter_parts():
        disposition = part.get("Content-Disposition", "")
        if "form-data" not in disposition or "name=\"files\"" not in disposition:
            continue
        payload = part.get_payload(decode=True)
        if payload:
            files.append((payload, part.get_filename() or "paper.pdf"))
    return files


def safe_filename(name: str) -> str:
    name = Path(name).name
    name = re.sub(r"[^\w\-.()\u4e00-\u9fff ]+", "_", name).strip(" .")
    return name or "paper.pdf"


def unique_stem(stem: str, used: set[str]) -> str:
    candidate = stem or "paper"
    i = 2
    while candidate in used:
        candidate = f"{stem or 'paper'}_{i}"
        i += 1
    used.add(candidate)
    return candidate


def extract_images(pdf_bytes: bytes, image_dir: Path) -> list[str]:
    """Extract embedded raster images from a PDF and return relative Markdown paths.

    The base MarkItDown PDF converter already turns detectable tables into Markdown.
    Here we additionally preserve embedded raster images as local files. We intentionally
    put them in a dedicated images/ folder and reference them relatively from the .md.
    """
    image_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    seen_xrefs: set[int] = set()
    image_paths: list[str] = []
    index = 1
    try:
        for page in doc:
            for image in page.get_images(full=True):
                xref = image[0]
                if xref in seen_xrefs:
                    continue
                seen_xrefs.add(xref)
                try:
                    data = doc.extract_image(xref)
                except Exception:
                    continue
                if not data or not data.get("image"):
                    continue
                ext = (data.get("ext") or "png").lower()
                if ext == "jpeg":
                    ext = "jpg"
                filename = f"image_{index:03d}.{ext}"
                (image_dir / filename).write_bytes(data["image"])
                image_paths.append(f"images/{filename}")
                index += 1
    finally:
        doc.close()
    return image_paths


def convert_one(pdf_bytes: bytes, original_name: str, output_root: Path, used_stems: set[str]) -> dict:
    original_name = safe_filename(original_name)
    stem = unique_stem(Path(original_name).stem, used_stems)
    paper_dir = output_root / stem
    paper_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = paper_dir / (stem + ".pdf")
    pdf_path.write_bytes(pdf_bytes)

    result = MarkItDown().convert(str(pdf_path))
    markdown = result.text_content or ""

    image_paths = extract_images(pdf_bytes, paper_dir / "images")
    if image_paths:
        markdown = markdown.rstrip() + "\n\n## 图片\n\n"
        markdown += "\n".join(f"![论文图片 {i}](<{path}>)" for i, path in enumerate(image_paths, 1))
        markdown += "\n"

    md_path = paper_dir / f"{stem}.md"
    md_path.write_text(markdown, encoding="utf-8")
    pdf_path.unlink(missing_ok=True)

    return {"name": original_name, "stem": stem, "images": len(image_paths), "chars": len(markdown)}


class Handler(BaseHTTPRequestHandler):
    server_version = "MarkItDownWeb/3.0"

    def _send(self, status: int, content_type: str, data: bytes, disposition: str | None = None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        if disposition:
            self.send_header("Content-Disposition", disposition)
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            return self._send(HTTPStatus.OK, "text/plain; charset=utf-8", b"ok")
        mapping = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/index.html": ("index.html", "text/html; charset=utf-8"),
            "/app.js": ("app.js", "text/javascript; charset=utf-8"),
            "/style.css": ("style.css", "text/css; charset=utf-8"),
        }
        if path in mapping:
            filename, content_type = mapping[path]
            return self._send(HTTPStatus.OK, content_type, (STATIC / filename).read_bytes())
        return self._send(HTTPStatus.NOT_FOUND, "text/plain; charset=utf-8", b"Not Found")

    def do_POST(self):
        if urlparse(self.path).path != "/convert-batch":
            return self._json(HTTPStatus.NOT_FOUND, {"error": "Not Found"})

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_TOTAL + 10 * 1024 * 1024:
                raise ValueError("上传内容为空或超过 500 MB 总限制")
            content_type = self.headers.get("Content-Type", "")
            if not content_type.startswith("multipart/form-data"):
                raise ValueError("请使用 multipart/form-data 上传文件")

            files = parse_multipart(content_type, self.rfile.read(length))
            if not files:
                raise ValueError("没有找到 PDF 文件")
            if len(files) > MAX_FILES:
                raise ValueError(f"一次最多处理 {MAX_FILES} 个 PDF")
            total = sum(len(data) for data, _ in files)
            if total > MAX_TOTAL:
                raise ValueError("PDF 总大小超过 500 MB 限制")
            for data, name in files:
                if len(data) > MAX_FILE:
                    raise ValueError(f"文件「{name}」超过 200 MB 限制")
                if not name.lower().endswith(".pdf") and not data.startswith(b"%PDF"):
                    raise ValueError(f"文件「{name}」不是有效 PDF")

            with tempfile.TemporaryDirectory(prefix="markitdown-batch-") as tmp:
                root = Path(tmp) / "markdown"
                root.mkdir()
                used: set[str] = set()
                results = []
                errors = []
                for data, name in files:
                    try:
                        results.append(convert_one(data, name, root, used))
                    except Exception as exc:
                        errors.append({"name": name, "error": str(exc)})

                if errors:
                    report = ["Markdown 批量转换失败记录", "", *[f"- {e['name']}: {e['error']}" for e in errors]]
                    (root / "转换失败记录.txt").write_text("\n".join(report), encoding="utf-8")

                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                    for path in sorted(root.rglob("*")):
                        if path.is_file():
                            zf.write(path, path.relative_to(root).as_posix())
                zip_buffer.seek(0)

            archive_name = "papers_markdown_with_images.zip"
            disposition = f"attachment; filename*=UTF-8''{quote(archive_name)}"
            return self._send(HTTPStatus.OK, "application/zip", zip_buffer.getvalue(), disposition)
        except Exception as exc:
            return self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def _json(self, status: int, obj: dict):
        return self._send(status, "application/json; charset=utf-8", json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}")


def main():
    parser = argparse.ArgumentParser(description="MarkItDown batch PDF → Markdown web UI")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()
    import os
    host = args.host or os.environ.get("HOST", "0.0.0.0")
    port = args.port or int(os.environ.get("PORT", "10000"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"MarkItDown Web 服务已启动: http://{host}:{port}")
    print("按 Ctrl+C 停止服务")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
