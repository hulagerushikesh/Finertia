import React from "react";
import { Button } from "@/components/ui/button";

/**
 * Catches render-time errors anywhere below it and shows a recovery screen
 * instead of unmounting the whole app to a blank page. Must be a class
 * component — React has no hook equivalent for componentDidCatch.
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
    console.error("Uncaught render error:", error, info);
  }

  handleReload = () => {
    window.location.assign("/");
  };

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <div className="min-h-[calc(100vh-3.5rem)] flex items-center justify-center px-4">
        <div className="w-full max-w-md">
          <p className="eyebrow mb-3">Render error</p>
          <h1 className="font-display text-display-sm font-medium text-foreground text-balance">
            Something broke on this page.
          </h1>
          <p className="text-sm text-graphite mt-3 leading-relaxed">
            An unexpected error stopped it from rendering. Reloading usually clears it.
          </p>
          <pre className="mt-5 sheet px-4 py-3 text-2xs font-mono text-loss overflow-x-auto">
            {String(this.state.error?.message || this.state.error)}
          </pre>
          <Button onClick={this.handleReload} className="mt-5">
            Reload Finertia
          </Button>
        </div>
      </div>
    );
  }
}
