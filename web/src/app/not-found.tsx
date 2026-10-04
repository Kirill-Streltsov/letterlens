import Link from "next/link";

export default function NotFound() {
  return (
    <main className="container" style={{ paddingTop: 80 }}>
      <h1>Page not found</h1>
      <p className="muted">This page does not exist.</p>
      <Link className="btn" href="/">
        Go to the start page
      </Link>
    </main>
  );
}
