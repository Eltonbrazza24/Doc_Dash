const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  // Função original
  processFile: (filePath, fileType) => ipcRenderer.invoke('process-file', filePath, fileType),

  // Nova função adicionada
  fetchData: async (url) => {
    // O `await` aqui garante que a Promise retornada por ipcRenderer.invoke é resolvida
    // antes de retornar o valor para o lado do renderer.
    // Se ipcRenderer.invoke já retorna uma Promise (o que é o caso de 'handle'),
    // o async/await é uma boa prática, mas poderia ser simplesmente:
    // return ipcRenderer.invoke('fetch-data', url);
    return await ipcRenderer.invoke('fetch-data', url);
  }
});