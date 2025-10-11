import type { AppProps } from "next/app";
import Link from "next/link";

import "../styles/globals.css";

function App({ Component, pageProps }: AppProps) {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <Link href="/">LecteurAide</Link>
        </div>
        <nav className="nav-links">
          <Link href="/">Upload</Link>
          <Link href="/library">Library</Link>
        </nav>
      </header>
      <main className="app-main">
        <Component {...pageProps} />
      </main>
    </div>
  );
}

export default App;
