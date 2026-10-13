/**
 * The address users write to. support@hulage.in forwards to the author
 * (Cloudflare Email Routing, 13 Oct), so a personal inbox is never published.
 * VITE_SUPPORT_EMAIL overrides it for a self-hosted deployment.
 */
export const SUPPORT_EMAIL = import.meta.env.VITE_SUPPORT_EMAIL || "support@hulage.in";
