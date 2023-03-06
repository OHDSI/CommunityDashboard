export const environment = {
  production: false,
  get rest() {
    if (location.port) {
      const localPort = `${location.protocol}//${location.hostname}:5001/`
      return localPort
    } else {
      // GH Codespaces is using a proxy.
      const portProxy = `${location.protocol}//${location.hostname.replace('4300', '5001')}/`
      return portProxy
    }
  },
  get plots() {
    if (location.port) {
      const localPort = `${location.protocol}//${location.hostname}:5001`
      return localPort
    } else {
      // GH Codespaces is using a proxy.
      const portProxy = `${location.protocol}//${location.hostname.replace('4300', '5001')}`
      return portProxy
    }
  },
};
