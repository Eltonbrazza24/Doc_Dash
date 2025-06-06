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
    
    // Ícone baseado no tipo de arquivo
    const icon = file.type.startsWith('image/') ? '🖼️' : '📄';
    
    card.innerHTML = `
      <div class="file-header">
        <span class="file-icon">${icon}</span>
        <div class="file-info">
          <span class="file-name">${file.name}</span>
          <span class="file-size">${formatFileSize(file.size)}</span>
        </div>
      </div>
      <div class="status processing">
        <div class="spinner"></div>
        Processando com IA...
      </div>
      <div class="result"></div>
    `;
    return card;
  }

  function updateCard(card, result) {
    const status = card.querySelector('.status');
    const resultDiv = card.querySelector('.result');
    
    if (result.status === 'error') {
      status.className = 'status error';
      status.innerHTML = '❌ Erro no processamento';
      resultDiv.innerHTML = `<div class="error-message">${result.message}</div>`;
    } else {
      status.className = 'status success';
      const method = result.metadata?.metodo_processamento || 'Processamento padrão';
      status.innerHTML = `✅ Concluído (${method})`;
      
      // Formata o resultado de forma mais legível
      resultDiv.innerHTML = formatResult(result);
    }
  }

  function formatResult(result) {
    let html = '<div class="result-content">';
    
    // Informações do documento
    if (result.type) {
      html += `<div class="doc-type">Tipo: <strong>${result.type}</strong></div>`;
    }
    
    // Dados extraídos
    if (result.data) {
      html += '<div class="extracted-data">';
      html += '<h4>Dados Extraídos:</h4>';
      
      if (typeof result.data === 'object') {
        html += formatObjectData(result.data);
      } else {
        html += `<pre>${JSON.stringify(result.data, null, 2)}</pre>`;
      }
      
      html += '</div>';
    }
    
    // Metadados
    if (result.metadata) {
      html += '<div class="metadata">';
      html += '<h4>Informações do Processamento:</h4>';
      html += `<p><strong>Arquivo:</strong> ${result.metadata.arquivo}</p>`;
      if (result.metadata.paginas) {
        html += `<p><strong>Páginas:</strong> ${result.metadata.paginas}</p>`;
      }
      html += `<p><strong>Processado em:</strong> ${result.metadata.processado_em}</p>`;
      html += '</div>';
    }
    
    html += '</div>';
    return html;
  }

  function formatObjectData(data) {
    let html = '<div class="data-fields">';
    
    for (const [key, value] of Object.entries(data)) {
      if (key === 'erro' || key === 'resposta_bruta') continue;
      
      const label = formatFieldLabel(key);
      const formattedValue = typeof value === 'object' ? 
        JSON.stringify(value, null, 2) : 
        String(value);
      
      html += `
        <div class="data-field">
          <span class="field-label">${label}:</span>
          <span class="field-value">${formattedValue}</span>
        </div>
      `;
    }
    
    html += '</div>';
    return html;
  }

  function formatFieldLabel(key) {
    const labels = {
      'nome': 'Nome',
      'numero_rg': 'Número RG',
      'numero_cpf': 'CPF',
      'nome_pai': 'Nome do Pai',
      'nome_mae': 'Nome da Mãe',
      'data_nascimento': 'Data de Nascimento',
      'natural_de': 'Natural de',
      'registro_civil': 'Registro Civil',
      'estado_civil': 'Estado Civil',
      'nome_funcionario': 'Nome do Funcionário',
      'empresa': 'Empresa',
      'cargo': 'Cargo',
      'periodo_referencia': 'Período de Referência',
      'salario_bruto': 'Salário Bruto',
      'descontos_total': 'Total de Descontos',
      'salario_liquido': 'Salário Líquido',
      'data_pagamento': 'Data de Pagamento',
      'texto_extraido': 'Texto Extraído',
      'tipo_documento': 'Tipo de Documento',
      'campos_identificados': 'Campos Identificados'
    };
    
    return labels[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }

  function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  function showError(msg) {
    const div = document.createElement('div');
    div.className = 'error-message';
    div.textContent = msg;
    output.appendChild(div);
    
    // Remove a mensagem após 5 segundos
    setTimeout(() => {
      if (div.parentNode) {
        div.parentNode.removeChild(div);
      }
    }, 5000);
  }
});