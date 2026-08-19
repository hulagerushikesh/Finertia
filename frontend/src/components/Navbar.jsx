import React, { useState, useEffect } from "react";
import { Link, NavLink, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function Navbar() {
  const { user, userProfile, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);

  // Close on navigation. Without this the panel stays open over the page the
  // user just asked for, and on a phone it covers most of it.
  useEffect(() => setOpen(false), [location.pathname]);

  // A menu that stays open while the layout grows past its breakpoint leaves a
  // stray panel floating under a nav bar that already shows every link.
  useEffect(() => {
    if (!open) return undefined;
    const mq = window.matchMedia("(min-width: 768px)");
    const onChange = (e) => e.matches && setOpen(false);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [open]);

  async function handleLogout() {
    setOpen(false);
    await logout();
    navigate("/login");
  }

  // Active state carried by an underline as well as colour. Colour alone was
  // the only marker before, which is both a low-contrast cue and one that
  // disappears entirely for a reader who cannot separate violet from grey.
  const linkClass = ({ isActive }) =>
    `relative text-sm font-medium transition-colors py-4 ${
      isActive
        ? "text-text-primary after:absolute after:left-0 after:right-0 after:-bottom-px after:h-0.5 after:bg-accent after:rounded-full"
        : "text-text-muted hover:text-text-primary"
    }`;

  // Same destinations in both layouts — the mobile panel is a reflow of the
  // desktop bar, not a reduced version of it.
  const links = user
    ? [
        ["/dashboard", "Dashboard"],
        ["/history", "History"],
        ["/pricing", "Pricing"],
        ...(userProfile?.role === "admin" ? [["/admin/overview", "Admin"]] : []),
      ]
    : [
        ["/demo", "Demo"],
        ["/docs", "Docs"],
        ["/pricing", "Pricing"],
        ["/login", "Login"],
      ];

  return (
    <nav className="sticky top-0 z-50 border-b border-border bg-bg/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between gap-3">
        <Link
          to="/"
          className="font-bold text-lg tracking-tight text-text-primary flex-shrink-0"
        >
          Finertia<span className="text-accent">.</span>
        </Link>

        {/* Desktop */}
        <div className="hidden md:flex items-center gap-6 min-w-0 self-stretch">
          {links.map(([to, label]) => (
            <NavLink key={to} to={to} className={linkClass}>
              {label}
            </NavLink>
          ))}
          {user ? (
            <>
              {/* An account chip rather than a bare email string: it reads as
                  something you can open, which the underlined-on-hover text
                  did not. */}
              <Link
                to="/profile"
                aria-label="Account settings"
                className="flex items-center gap-2 bg-raised border border-border hover:border-border-strong rounded-full pl-1 pr-3 py-1 transition-colors min-w-0"
              >
                <span
                  aria-hidden="true"
                  className="w-5 h-5 shrink-0 rounded-full bg-accent/20 text-accent-soft text-2xs font-mono font-semibold flex items-center justify-center uppercase"
                >
                  {user.email.charAt(0)}
                </span>
                <span className="text-xs font-mono text-text-muted truncate max-w-[140px]">
                  {user.email}
                </span>
              </Link>
              <button
                onClick={handleLogout}
                className="text-sm text-text-muted hover:text-danger transition-colors flex-shrink-0 rounded"
              >
                Sign out
              </button>
            </>
          ) : (
            <Link
              to="/register"
              className="btn-primary text-sm px-4 py-1.5 flex-shrink-0 whitespace-nowrap"
            >
              Get Started
            </Link>
          )}
        </div>

        {/* Mobile trigger */}
        <button
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          aria-label={open ? "Close menu" : "Open menu"}
          className="md:hidden w-9 h-9 -mr-1 flex flex-col items-center justify-center gap-[5px] text-text-muted hover:text-text-primary transition-colors"
        >
          <span
            className={`block w-5 h-px bg-current transition-transform ${
              open ? "translate-y-[6px] rotate-45" : ""
            }`}
          />
          <span
            className={`block w-5 h-px bg-current transition-opacity ${
              open ? "opacity-0" : ""
            }`}
          />
          <span
            className={`block w-5 h-px bg-current transition-transform ${
              open ? "-translate-y-[6px] -rotate-45" : ""
            }`}
          />
        </button>
      </div>

      {/* Mobile panel */}
      {open && (
        <div className="md:hidden border-t border-border bg-surface">
          <div className="px-4 sm:px-6 py-3 flex flex-col">
            {links.map(([to, label]) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `py-2.5 text-sm font-medium transition-colors ${
                    isActive ? "text-accent" : "text-text-muted"
                  }`
                }
              >
                {label}
              </NavLink>
            ))}

            {user ? (
              <div className="border-t border-border mt-2 pt-3 flex items-center justify-between gap-3">
                <Link
                  to="/profile"
                  className="text-xs text-text-muted font-mono truncate min-w-0"
                >
                  {user.email}
                </Link>
                <button
                  onClick={handleLogout}
                  className="text-sm text-text-muted hover:text-danger transition-colors flex-shrink-0"
                >
                  Sign out
                </button>
              </div>
            ) : (
              <Link
                to="/register"
                className="btn-primary mt-2 text-sm px-4 py-2.5"
              >
                Get Started
              </Link>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}
