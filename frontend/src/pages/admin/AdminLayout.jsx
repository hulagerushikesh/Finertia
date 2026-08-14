import React from "react";
import { NavLink, Outlet } from "react-router-dom";

const linkClass = ({ isActive }) =>
  `text-sm px-3 py-1.5 rounded-lg transition-colors ${
    isActive
      ? "bg-accent/10 text-accent font-medium"
      : "text-text-muted hover:text-text-primary"
  }`;

export default function AdminLayout() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center gap-2 mb-6">
        <span className="text-xs bg-accent/10 text-accent border border-accent/20 px-2 py-0.5 rounded font-medium">
          ADMIN
        </span>
        <h1 className="text-xl font-semibold text-text-primary">Admin Panel</h1>
      </div>

      <nav className="flex gap-1 mb-7 bg-surface border border-border rounded-xl p-1 w-fit">
        <NavLink to="/admin/overview" className={linkClass}>Overview</NavLink>
        <NavLink to="/admin/users" className={linkClass}>Users</NavLink>
        <NavLink to="/admin/runs" className={linkClass}>Runs</NavLink>
      </nav>

      <Outlet />
    </div>
  );
}
