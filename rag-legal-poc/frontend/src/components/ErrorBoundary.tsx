import React from "react";

type State = { hasError: boolean; error?: any };

export default class ErrorBoundary extends React.Component<React.PropsWithChildren, State> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error: any) {
    return { hasError: true, error };
  }
  componentDidCatch(error: any, info: any) {
    console.error("Graph ErrorBoundary:", error, info);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="rounded-xl border border-border p-3 text-sm text-red-300 bg-card-2">
          مشکلی در رندر گراف پیش آمد.
        </div>
      );
    }
    return this.props.children;
  }
}
