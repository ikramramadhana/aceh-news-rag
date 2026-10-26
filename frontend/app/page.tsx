import Link from "next/link";

export default function Landing() {
  return (
    <main className="dark-theme relative min-h-dvh overflow-hidden hero-glow">
      <div className="wave-line" style={{ top: "58%" }} />
      <div className="wave-line" style={{ top: "62%", animationDelay: "-2s", opacity: 0.3 }} />
      <div className="wave-line" style={{ top: "66%", animationDelay: "-4s", opacity: 0.2 }} />

      <header className="relative z-10 max-w-6xl mx-auto px-5 sm:px-8 py-6 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <img src="/logo.png" alt="Logo Pancacita Aceh" className="w-8 h-8 object-contain" />
          <span className="font-display font-bold text-base">Aceh Hari Ini</span>
        </div>
        <Link
          href="/chat"
          className="text-sm font-semibold px-5 py-2.5 rounded-lg"
          style={{ background: "var(--d-accent)", color: "#06130e" }}
        >
          Tekan untuk bertanya
        </Link>
      </header>

      <section className="relative z-10 max-w-6xl mx-auto px-5 sm:px-8 pt-12 sm:pt-20 pb-24 grid lg:grid-cols-2 gap-12 items-center">
        <div>
          <h1 className="font-display font-bold text-4xl sm:text-6xl leading-[1.1] mb-6">
            Aceh Hari Ini: Tanya Berita Pemerintahan, Langsung Dijawab
          </h1>
          <p className="text-base sm:text-lg max-w-xl mb-8" style={{ color: "var(--d-muted)" }}>
            Cari kebijakan, pernyataan, dan perkembangan terbaru Pemerintah Aceh tanpa
            membuka artikel satu per satu. Jawaban disusun dari berita resmi
            humas.acehprov.go.id, lengkap dengan sumbernya.
          </p>
          <Link
            href="/chat"
            className="inline-flex items-center gap-3 pl-6 pr-2 py-2 rounded-full border text-sm font-medium"
            style={{ borderColor: "var(--d-line)", background: "var(--d-surface)" }}
          >
            Tanyakan Apapun
            <span
              className="px-4 py-2 rounded-full font-semibold"
              style={{ background: "var(--d-accent)", color: "#06130e" }}
            >
              Berita Aceh
            </span>
          </Link>
        </div>

        <div className="relative flex justify-center">
          <div
            className="absolute inset-0 m-auto w-72 h-72 sm:w-96 sm:h-96 rounded-full blur-3xl"
            style={{ background: "var(--d-accent-soft)" }}
          />
          <img
            src="/logo.png"
            alt="Pancacita Aceh"
            className="relative floaty w-56 h-56 sm:w-80 sm:h-80 object-contain drop-shadow-[0_0_40px_rgba(31,197,142,0.35)]"
          />
        </div>
      </section>

      <section className="relative z-10 max-w-6xl mx-auto px-5 sm:px-8 pb-20 grid sm:grid-cols-3 gap-4">
        {[
          ["Berbasis berita resmi", "Hanya menjawab dari artikel humas.acehprov.go.id yang diperbarui otomatis setiap hari."],
          ["Sumber selalu ditampilkan", "Setiap jawaban disertai tautan berita rujukan, jadi mudah dicek ulang."],
          ["Bisa disaring", "Batasi pertanyaan berdasarkan kategori berita atau tanggal tertentu."],
        ].map(([t, d]) => (
          <div
            key={t}
            className="p-5 rounded-2xl border"
            style={{ borderColor: "var(--d-line)", background: "var(--d-surface)" }}
          >
            <h3 className="font-display font-bold mb-1.5">{t}</h3>
            <p className="text-sm" style={{ color: "var(--d-muted)" }}>{d}</p>
          </div>
        ))}
      </section>
    </main>
  );
}
