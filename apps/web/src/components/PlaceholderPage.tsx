export function PlaceholderPage({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <section className="mx-auto max-w-4xl">
      <div className="rounded-2xl border border-atlas-line bg-atlas-panel/90 p-8 shadow-sm">
        <p className="text-xs uppercase tracking-[0.18em] text-atlas-muted">ATLAS module</p>
        <h2 className="mt-2 font-display text-4xl text-atlas-ink">{title}</h2>
        <p className="mt-4 max-w-2xl text-base leading-relaxed text-atlas-muted">{description}</p>
        <div className="mt-8 grid gap-3 sm:grid-cols-3">
          {["Contracts ready", "Infra wired", "Business logic later"].map((item) => (
            <div key={item} className="rounded-xl border border-atlas-line bg-atlas-bg/60 px-4 py-3 text-sm text-atlas-ink">
              {item}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
