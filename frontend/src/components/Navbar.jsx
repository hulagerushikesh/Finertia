import React, { useState, useEffect } from "react";
import { Link, NavLink, useNavigate, useLocation } from "react-router-dom";
import { Menu } from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from "@/components/ui/sheet";
import { Separator } from "@/components/ui/separator";
import ThemeToggle from "./ThemeToggle";
import { cn } from "@/lib/utils";

/** The wordmark. The full stop is set in pencil — the one mark of the editor. */
export function Wordmark({ className }) {
  return (
    <span className={cn("font-display text-[1.35rem] leading-none tracking-tight text-foreground", className)}>
      Finertia<span className="text-pencil">.</span>
    </span>
  );
}

export default function Navbar() {
  const { user, userProfile, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);

  // Close on navigation: a sheet that stays open covers the page just asked for.
  useEffect(() => setOpen(false), [location.pathname]);

  async function handleLogout() {
    setOpen(false);
    await logout();
    navigate("/login");
  }

  // Same destinations in both layouts — the mobile sheet is a reflow of the
  // desktop bar, not a reduced version of it.
  const links = user
    ? [
        ["/dashboard", "Workspace"],
        ["/history", "History"],
        ["/pricing", "Pricing"],
        ...(userProfile?.role === "admin" ? [["/admin/overview", "Admin"]] : []),
      ]
    : [
        ["/demo", "A real result"],
        ["/docs", "How it works"],
        ["/pricing", "Pricing"],
      ];

  // Active state is an underline in pencil, the editor's mark on the current
  // page — a cue that survives for a reader who cannot split blue from grey.
  const linkClass = ({ isActive }) =>
    cn(
      "relative text-sm font-medium transition-colors py-[1.1rem] whitespace-nowrap",
      isActive
        ? "text-foreground after:absolute after:left-0 after:right-0 after:bottom-0 after:h-0.5 after:bg-pencil"
        : "text-graphite hover:text-foreground",
    );

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/85 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center gap-4">
        <Link to="/" className="shrink-0 rounded-sm" aria-label="Finertia home">
          <Wordmark />
        </Link>

        {/* Desktop */}
        <nav className="hidden md:flex items-center gap-6 ml-6 self-stretch" aria-label="Primary">
          {links.map(([to, label]) => (
            <NavLink key={to} to={to} className={linkClass}>
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="hidden md:flex items-center gap-2 ml-auto">
          <ThemeToggle />
          {user ? (
            <>
              <Button asChild variant="ghost" size="sm" className="font-mono text-xs text-graphite max-w-[12rem]">
                <Link to="/profile" aria-label="Account settings">
                  <span className="size-5 shrink-0 rounded-full bg-pencil/10 text-pencil text-2xs font-medium flex items-center justify-center uppercase">
                    {user.email.charAt(0)}
                  </span>
                  <span className="truncate">{user.email}</span>
                </Link>
              </Button>
              <Button variant="ghost" size="sm" onClick={handleLogout} className="text-graphite hover:text-loss">
                Sign out
              </Button>
            </>
          ) : (
            <>
              <Button asChild variant="ghost" size="sm">
                <Link to="/login">Sign in</Link>
              </Button>
              <Button asChild size="sm">
                <Link to="/register">Start free</Link>
              </Button>
            </>
          )}
        </div>

        {/* Mobile */}
        <div className="md:hidden ml-auto flex items-center gap-1">
          <ThemeToggle />
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="Open menu">
                <Menu className="size-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-[18rem] flex flex-col gap-1 pt-12">
              <SheetTitle className="sr-only">Menu</SheetTitle>
              {links.map(([to, label]) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    cn(
                      "py-2.5 text-base font-medium rounded-sm",
                      isActive ? "text-pencil" : "text-foreground",
                    )
                  }
                >
                  {label}
                </NavLink>
              ))}
              <Separator className="my-3" />
              {user ? (
                <>
                  <Link to="/profile" className="font-mono text-xs text-graphite truncate py-1">
                    {user.email}
                  </Link>
                  <Button variant="outline" onClick={handleLogout} className="mt-2 justify-start">
                    Sign out
                  </Button>
                </>
              ) : (
                <div className="flex flex-col gap-2 mt-1">
                  <Button asChild>
                    <Link to="/register">Start free</Link>
                  </Button>
                  <Button asChild variant="outline">
                    <Link to="/login">Sign in</Link>
                  </Button>
                </div>
              )}
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  );
}
