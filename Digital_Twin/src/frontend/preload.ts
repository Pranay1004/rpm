import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('electronAPI', {
  // Example API - extend as needed
  invokeCommand: (channel: string, ...args: any[]) =>
    ipcRenderer.invoke(channel, ...args),
  sendCommand: (channel: string, ...args: any[]) =>
    ipcRenderer.send(channel, ...args),
  onReceive: (channel: string, func: (arg: any) => void) =>
    ipcRenderer.on(channel, (event, arg) => func(arg)),
});
