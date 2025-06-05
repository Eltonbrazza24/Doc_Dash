const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { exec } = require('child_process'); // Adicionado do primeiro trecho

// Configurações de SSL para desenvolvimento (do segundo trecho)
process.env.ELECTRON_DISABLE_SECURITY_WARNINGS = 'true';
app.commandLine.appendSwitch('ignore-certificate-errors');

function createWindow() {
  const win = new BrowserWindow({
    // width: 800, // Você pode adicionar dimensões se desejar
    // height: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'), // Do primeiro e segundo trecho
      contextIsolation: true,                       // Do primeiro e segundo trecho
      webSecurity: false // Desativa apenas se necessário (do segundo trecho) - CUIDADO EM PRODUÇÃO
    }
  });

  win.loadFile('index.html'); // Do primeiro e segundo trecho

  // Debug (remova em produção) (do segundo trecho)
  win.webContents.openDevTools();
}

// Função para executar scripts Python (do primeiro trecho)
function runPythonScript(script, filePath) {
  return new Promise((resolve) => {
    const cmd = `python "${path.join(__dirname, script)}" "${filePath}"`;
    // Aumentando o maxBuffer se necessário, como no original
    const process = exec(cmd, { maxBuffer: 1024 * 1024 * 20 }, (error, stdout) => {
      if (error) {
        console.error(`Erro ao executar script Python (${script}): ${error.message}`);
        return resolve({ status: 'error', message: error.message });
      }
      try {
        resolve(JSON.parse(stdout));
      } catch (e) {
        console.error(`Erro ao parsear JSON do script Python (${script}): ${e.message}`);
        console.log(`Saída bruta do script (${script}):`, stdout);
        resolve({ status: 'error', message: 'Resposta inválida do script', raw: stdout });
      }
    });

    // Timeout para o processo (do primeiro trecho)
    setTimeout(() => {
      if (!process.killed) {
        process.kill();
        console.warn(`Script Python (${script}) finalizado por timeout (60s)`);
        resolve({ status: 'error', message: 'Timeout (60s) ao executar o script' });
      }
    }, 60000); // 60 segundos
  });
}

// Handler IPC para processar arquivos (do primeiro trecho)
ipcMain.handle('process-file', async (_, filePath, fileType) => {
  console.log(`Recebido pedido para processar: ${filePath}, tipo: ${fileType}`);
  const script = fileType.startsWith('image/') ?
    'image_processor.py' :
    'document_processor.py';
  return runPythonScript(script, filePath);
});

// Ciclo de vida do aplicativo (do segundo trecho, mais completo)
app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    // No macOS é comum recriar uma janela no aplicativo quando o
    // ícone do dock é clicado e não há outras janelas abertas.
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  // No macOS é comum para aplicativos e sua barra de menu
  // permanecerem ativos até que o usuário saia explicitamente com Cmd + Q
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// O comentário "Seu código de processamento de arquivos continua aqui..."
// foi substituído pela lógica de runPythonScript e ipcMain.handle acima.