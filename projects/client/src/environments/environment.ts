export const environment = {
  production: false,
  get plots() {
    if (location.port) {
      const localPort = `${location.protocol}//${location.hostname}:5001`
      return localPort
    } else {
      // GH Codespaces is using a proxy.
      const portProxy = `${location.protocol}//${location.hostname.replace('4200', '5001')}`
      return portProxy
    }
  }
};
