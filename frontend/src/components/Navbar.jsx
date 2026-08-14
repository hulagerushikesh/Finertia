import React from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function Navbar() {
  const { user, userProfile, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  const linkClass = ({ isActive }) =>
    `text-sm font-medium transition-colors ${
      isActive ? "text-accent" : "text-text-muted hover:text-text-primary"
    }`;

  return (
    <nav className="sticky top-0 z-50 border-b border-border bg-surface/90 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        <Link to="/" className="font-bold text-lg tracking-tight text-text-primary">
          Finertia<span className="text-accent">.</span>
        </Link>

        <div className="flex items-center gap-6">
          {user ? (
            <>
              <NavLink to="/dashboard" className={linkClass}>Dashboard</NavLink>
              <NavLink to="/history" className={linkClass}>History</NavLink>
              <NavLink to="/pricing" className={linkClass}>Pricing</NavLink>
              {userProfile?.role === "admin" && (
                <NavLink to="/admin/overview" className={linkClass}>Admin</NavLink>
              )}
              <Link
                to="/profile"
                title="Account settings"
                className="text-xs text-text-muted hover:text-text-primary font-mono truncate max-w-[160px] transition-colors"
              >
                {user.email}
              </Link>
              <button
                onClick={handleLogout}
                className="text-sm text-text-muted hover:text-danger transition-colors"
              >
                Sign Out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/demo" className={linkClass}>Demo</NavLink>
              <NavLink to="/docs" className={linkClass}>Docs</NavLink>
              <NavLink to="/pricing" className={linkClass}>Pricing</NavLink>
              <NavLink to="/login" className={linkClass}>Login</NavLink>
              <Link
                to="/register"
                className="text-sm font-medium bg-accent hover:bg-indigo-500 text-white px-4 py-1.5 rounded-lg transition-colors"
              >
                Get Started
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
