document.addEventListener('DOMContentLoaded', () => {
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('fileInput');
  const output = document.getElementById('output');

  // Tipos permitidos
  const allowedTypes = [
    'application/pdf',
    'image/jpeg',
    'image/jpg',
    'image/png'
  ];

  // Configura Drag-and-Drop
  const handleDrag = (e) => {
    e.preventDefault();
    dropZone.classList.toggle('dragging', e.type === 'dragover');
  };

  dropZone.addEventListener('dragover', handleDrag);
  dropZone.addEventListener('dragleave', handleDrag);
  dropZone.addEventListener('drop', (e) => {
    handleDrag(e);
    handleFiles(e.dataTransfer.files);
  });

  // Configura seleção manual
  dropZone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) handleFiles(fileInput.files);
  });

  // Processamento de arquivos
  async function handleFiles(files) {
    for (const file of files) {
      if (!allowedTypes.includes(file.type)) {
        showError(`Formato não suportado: ${file.name} (${file.type || 'sem tipo'})`);
        continue;
      }

      const card = createFileCard(file);
      output.appendChild(card);

      try {
        const result = await window.api.processFile(file.path, file.type);
        updateCard(card, result);
      } catch (error) {
        updateCard(card, {
          status: 'error',
          message: error.message || 'Falha no processamento'
        });
      }
    }
  }

  function createFileCard(file) {
    const card = document.createElement('div');
    card.className = 'file-card';
    card.innerHTML = `
      <div class="file-header">
        <span class="file-icon">📄</span>
        <span>${file.name}</span>
      </div>
      <div class="status">Processando...</div>
      <div class="result"></div>
    `;
    return card;
  }

  function updateCard(card, result) {
    const status = card.querySelector('.status');
    const resultDiv = card.querySelector('.result');
    if (result.status === 'error') {
      status.textContent = 'Erro';
      resultDiv.innerHTML = `<div class="error-message">${result.message}</div>`;
    } else {
      status.textContent = 'Concluído';
      resultDiv.textContent = JSON.stringify(result, null, 2);
    }
  }

  function showError(msg) {
    const div = document.createElement('div');
    div.className = 'error-message';
    div.textContent = msg;
    output.appendChild(div);
  }
});