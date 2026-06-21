"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/products", label: "Products" },
  { href: "/crawler", label: "Crawler" },
];

export default function NavBar() {
  const pathname = usePathname();
  return (
    <header className="border-b border-ink-200 bg-ink-50/80 backdrop-blur">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-5">
        <Link href="/" className="group flex items-baseline gap-2">
          <span className="font-display text-2xl font-semibold tracking-tight text-ink-900">
            Price<span className="italic text-accent">Tracker</span>
          </span>
          <span className="hidden text-xs uppercase tracking-[0.2em] text-ink-400 sm:inline">
            Comparison engine
          </span>
        </Link>
        <nav className="flex items-center gap-8 text-sm font-medium text-ink-600">
          {links.map((link) => {
            const active = pathname?.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                data-active={active}
                className="nav-link transition-colors hover:text-ink-900"
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
