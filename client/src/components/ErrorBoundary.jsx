import { Component } from "react";

// Evita que un error de render deje la página en blanco/colgada.
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // eslint-disable-next-line no-console
    console.error("Error de render:", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="page">
          <div className="card center">
            <div className="block-title" style={{ marginTop: 0 }}>Algo falló al mostrar esta vista</div>
            <p className="muted">{String(this.state.error?.message || this.state.error)}</p>
            <button className="btn" onClick={() => this.setState({ error: null })}>Reintentar</button>
            <button className="btn ghost" style={{ marginLeft: 8 }} onClick={() => location.reload()}>Recargar</button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
