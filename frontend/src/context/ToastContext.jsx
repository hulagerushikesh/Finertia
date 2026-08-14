import React, { createContext, useState, useEffect } from "react";
import Toast from "../components/Toast";

export const ToastContext = createContext(null);

const AUTO_DISMISS_MS = 4000;

let nextId = 1;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  function showToast(message, type = "info") {
    const id = nextId++;
    setToasts((current) => [...current, { id, message, type }]);
  }

  function dismissToast(id) {
    setToasts((current) => current.filter((t) => t.id !== id));
  }

  // One timer per toast, cleared whenever the queue changes so a toast
  // dismissed by hand doesn't leave a pending timeout behind.
  useEffect(() => {
    if (toasts.length === 0) return;
    const timers = toasts.map((t) =>
      setTimeout(() => dismissToast(t.id), AUTO_DISMISS_MS)
    );
    return () => timers.forEach(clearTimeout);
  }, [toasts]);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="fixed bottom-5 right-5 z-[100] flex flex-col gap-2 pointer-events-none">
        {toasts.map((t) => (
          <Toast
            key={t.id}
            message={t.message}
            type={t.type}
            onDismiss={() => dismissToast(t.id)}
          />
        ))}
      </div>
    </ToastContext.Provider>
  );
}
