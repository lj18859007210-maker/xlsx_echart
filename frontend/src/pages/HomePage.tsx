export function HomePage() {
  return (
    <main className="app-shell">
      <section className="hero">
        <p className="eyebrow">Day 2 Bootstrap</p>
        <h1>xlsx_echart</h1>
        <p className="summary">
          Excel analysis workspace with a FastAPI backend, a React frontend, and a
          structure-first workflow.
        </p>
      </section>

      <section className="panel-grid">
        <article className="panel">
          <h2>Backend</h2>
          <p>FastAPI skeleton with healthcheck and route placeholders.</p>
        </article>
        <article className="panel">
          <h2>Frontend</h2>
          <p>React + Vite entry with base page and lint/build scripts.</p>
        </article>
        <article className="panel">
          <h2>Scope</h2>
          <p>Ready for Day 3 database and model work.</p>
        </article>
      </section>
    </main>
  );
}
