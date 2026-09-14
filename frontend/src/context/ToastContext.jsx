import React, { createContext } from "react";
import { toast } from "sonner";
import { Toaster } from "@/components/ui/sonner";

export const ToastContext = createContext(null);

/**
 * Same `showToast(message, type)` the pages have always called, now rendered
 * by sonner. The context is kept so no call site changes; the provider is the
 * only file that knows which library draws the toast.
 */
export function ToastProvider({ children }) {
  function showToast(message, type = "info") {
    if (type === "success") toast.success(message);
    else if (type === "error") toast.error(message);
    else toast(message);
  }

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <Toaster position="bottom-right" closeButton duration={4000} />
    </ToastContext.Provider>
  );
}
