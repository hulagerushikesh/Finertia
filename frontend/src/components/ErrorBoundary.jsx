import React from "react";

/**
 * Catches render-time errors anywhere below it and shows a recovery screen
 * instead of unmounting the whole app to a blank page.
 *
 * Must be a class component — React has no hook equivalent for
 * componentDidCatch.
 */
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // Replace with a Sentry capture in S7.
    console.error("Uncaught render error:", error, info);
  }

  handleReload = () => {
    window.location.assign("/");
  };

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <div className="min-h-[calc(100vh-56px)] flex items-center justify-center px-4">
        <div className="w-full max-w-md text-center">
          <div className="w-10 h-10 rounded-full bg-danger/10 border border-danger/30 flex items-center justify-center mx-auto mb-4">
            <span className="text-danger text-lg leading-none font-bold">!</span>
          </div>
          <h1 className="text-xl font-bold text-text-primary">Something broke</h1>
          <p className="text-sm text-text-muted mt-2 leading-relaxed">
            An unexpected error stopped this page from rendering. Reloading usually
            clears it.
          </p>

          <pre className="mt-5 text-left bg-surface border border-border rounded-lg px-4 py-3 text-2xs font-mono text-danger/90 overflow-x-auto">
            {String(this.state.error?.message || this.state.error)}
          </pre>

          <button
            onClick={this.handleReload}
            className="btn-primary mt-5 px-5 py-2.5 text-sm"
          >
            Reload Finertia
          </button>
        </div>
      </div>
    );
  }
}
