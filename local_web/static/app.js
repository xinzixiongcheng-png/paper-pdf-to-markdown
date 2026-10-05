const dropzone = document.querySelector('#dropzone');
const input = document.querySelector('#file');
const pick = document.querySelector('#pick');
const queue = document.querySelector('#queue');
const list = document.querySelector('#file-list');
const count = document.querySelector('#count');
const convertButton = document.querySelector('#convert');
const status = document.querySelector('#status');
const result = document.querySelector('#result');
const summary = document.querySelector('#summary');
const download = document.querySelector('#download');

let selectedFiles = [];
let zipBlob = null;

pick.addEventListener('click', (e) => { e.stopPropagation(); input.click(); });
dropzone.addEventListener('click', () => input.click());
dropzone.addEventListener('keydown', e => {
  if (e.key === 'Enter' || e.key === ' ') input.click();
});
input.addEventListener('change', () => addFiles([...input.files]));

['dragenter', 'dragover'].forEach(type => dropzone.addEventListener(type, e => {
  e.preventDefault();
  dropzone.classList.add('dragging');
}));
['dragleave', 'drop'].forEach(type => dropzone.addEventListener(type, e => {
  e.preventDefault();
  dropzone.classList.remove('dragging');
}));
dropzone.addEventListener('drop', e => addFiles([...e.dataTransfer.files]));

convertButton.addEventListener('click', convertBatch);

download.addEventListener('click', () => {
  if (!zipBlob) return;
  const url = URL.createObjectURL(zipBlob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'papers_markdown_with_images.zip';
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});

function addFiles(files) {
  const pdfs = files.filter(file => file.name.toLowerCase().endsWith('.pdf') || file.type === 'application/pdf');
  if (!pdfs.length) {
    showStatus('请选择 PDF 文件。', true);
    return;
  }
  selectedFiles = [...selectedFiles, ...pdfs];
  renderQueue();
  result.classList.add('hidden');
  input.value = '';
}

function renderQueue() {
  queue.classList.remove('hidden');
  count.textContent = `${selectedFiles.length} 篇`;
  list.innerHTML = '';
  selectedFiles.forEach((file, index) => {
    const row = document.createElement('div');
    row.className = 'file-row';
    row.innerHTML = `<span class="file-number">${index + 1}</span><span class="file-name"></span><span class="file-size">${formatBytes(file.size)}</span>`;
    row.querySelector('.file-name').textContent = file.name;
    list.appendChild(row);
  });
}

function formatBytes(bytes) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function showStatus(text, error = false) {
  status.className = `status ${error ? 'error' : ''}`;
  status.textContent = text;
  status.classList.remove('hidden');
}

async function convertBatch() {
  if (!selectedFiles.length) return;

  const totalSize = selectedFiles.reduce((sum, file) => sum + file.size, 0);
  if (selectedFiles.length > 100) return showStatus('一次最多处理 100 个 PDF。', true);
  if (selectedFiles.some(file => file.size > 200 * 1024 * 1024)) return showStatus('存在超过 200 MB 的单个 PDF。', true);
  if (totalSize > 500 * 1024 * 1024) return showStatus('PDF 总大小超过 500 MB。', true);

  convertButton.disabled = true;
  download.disabled = true;
  result.classList.add('hidden');
  showStatus(`正在批量转换 ${selectedFiles.length} 篇论文……图片也会一起提取。`);

  const form = new FormData();
  selectedFiles.forEach(file => form.append('files', file, file.name));

  try {
    const response = await fetch('/convert-batch', { method: 'POST', body: form });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || '批量转换失败');
    }
    zipBlob = await response.blob();
    summary.textContent = `已生成 ZIP：${selectedFiles.length} 篇论文，Markdown 与图片已按论文分别整理。`;
    result.classList.remove('hidden');
    showStatus('全部处理完成，可以下载 ZIP。');
    download.disabled = false;
  } catch (err) {
    showStatus(`转换失败：${err.message}`, true);
  } finally {
    convertButton.disabled = false;
  }
}
