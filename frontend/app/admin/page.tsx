"use client";

import { useEffect, useState } from "react";

type Category = { category: string; article_count: number };

type Stats = {
  total_articles: number;
  total_chunks: number;
  last_scrape_at: string | null;
  latest_article_published_at: string | null;
  top_categories: Category[];
  feedback: {
    likes: number;
    dislikes: number;
    total: number;
    like_ratio_percent: number | null;
  };
};

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function formatDateTime(iso: string | null): string {
  if (!iso) return "Belum ada data";
  try {
    return new Date(iso).toLocaleString("id-ID", {
      day: "numeric",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div
      className="p-4 sm:p-5 rounded-2xl"
      style={{ border: "1px solid var(--line)", background: "#ffffff" }}
    >
      <p className="text-xs mb-1" style={{ color: "var(--ink-muted)" }}>
        {label}
      </p>
      <p className="font-display text-2xl font-bold" style={{ color: "var(--ink)" }}>
        {value}
      </p>
      {sub && (
        <p className="text-xs mt-1" style={{ color: "var(--ink-muted)" }}>
          {sub}
        </p>
      )}
    </div>
  );
}

export default function AdminPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch(`${API_URL}/admin/stats`)
      .then((res) => {
        if (!res.ok) throw new Error("failed");
        return res.json();
      })
      .then((data) => setStats(data))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-dvh" style={{ background: "var(--bg)" }}>
      <header className="px-4 sm:px-6 py-4 border-b" style={{ borderColor: "var(--line)" }}>
        <div className="max-w-3xl mx-auto">
          <h1 className="font-display text-lg font-bold" style={{ color: "var(--ink)" }}>
            Dashboard Statistik
          </h1>
          <p className="text-xs" style={{ color: "var(--ink-muted)" }}>
            Aceh Hari Ini — kondisi sistem saat ini
          </p>
        </div>
      </header>

      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6">
        {loading && (
          <p className="text-sm" style={{ color: "var(--ink-muted)" }}>
            Memuat statistik...
          </p>
        )}

        {error && (
          <p className="text-sm" style={{ color: "var(--accent)" }}>
            Gagal memuat statistik. Pastikan backend sedang berjalan.
          </p>
        )}

        {stats && (
          <div className="space-y-6">
            {/* Ringkasan angka utama */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <StatCard label="Total Berita" value={stats.total_articles.toLocaleString("id-ID")} />
              <StatCard label="Total Chunk Ter-index" value={stats.total_chunks.toLocaleString("id-ID")} />
              <StatCard
                label="Berita Terbaru"
                value={formatDateTime(stats.latest_article_published_at).split(",")[0]}
              />
              <StatCard
                label="Scraping Terakhir Masuk"
                value={formatDateTime(stats.last_scrape_at).split(",")[0]}
              />
            </div>

            {/* Kategori terbanyak */}
            <div
              className="p-4 sm:p-5 rounded-2xl"
              style={{ border: "1px solid var(--line)", background: "#ffffff" }}
            >
              <p className="text-sm font-medium mb-3" style={{ color: "var(--ink)" }}>
                5 Kategori Terbanyak
              </p>
              <div className="space-y-2">
                {stats.top_categories.map((c) => {
                  const max = stats.top_categories[0]?.article_count || 1;
                  const widthPct = (c.article_count / max) * 100;
                  return (
                    <div key={c.category}>
                      <div className="flex justify-between text-xs mb-1">
                        <span style={{ color: "var(--ink)" }}>{c.category}</span>
                        <span style={{ color: "var(--ink-muted)" }}>{c.article_count}</span>
                      </div>
                      <div className="h-2 rounded-full overflow-hidden" style={{ background: "var(--primary-soft)" }}>
                        <div
                          className="h-full rounded-full"
                          style={{ width: `${widthPct}%`, background: "var(--primary)" }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Feedback like/dislike */}
            <div
              className="p-4 sm:p-5 rounded-2xl"
              style={{ border: "1px solid var(--line)", background: "#ffffff" }}
            >
              <p className="text-sm font-medium mb-3" style={{ color: "var(--ink)" }}>
                Feedback Jawaban
              </p>

              {stats.feedback.total === 0 ? (
                <p className="text-xs" style={{ color: "var(--ink-muted)" }}>
                  Belum ada feedback yang masuk.
                </p>
              ) : (
                <>
                  <div className="flex items-center gap-4 mb-3">
                    <div>
                      <p className="text-2xl font-bold" style={{ color: "var(--primary)" }}>
                        {stats.feedback.like_ratio_percent}%
                      </p>
                      <p className="text-xs" style={{ color: "var(--ink-muted)" }}>
                        dinilai membantu
                      </p>
                    </div>
                    <div className="flex-1 flex h-3 rounded-full overflow-hidden">
                      <div
                        style={{
                          width: `${(stats.feedback.likes / stats.feedback.total) * 100}%`,
                          background: "var(--primary)",
                        }}
                      />
                      <div
                        style={{
                          width: `${(stats.feedback.dislikes / stats.feedback.total) * 100}%`,
                          background: "var(--accent)",
                        }}
                      />
                    </div>
                  </div>
                  <div className="flex gap-4 text-xs" style={{ color: "var(--ink-muted)" }}>
                    <span>👍 {stats.feedback.likes} suka</span>
                    <span>👎 {stats.feedback.dislikes} tidak suka</span>
                    <span>Total {stats.feedback.total} feedback</span>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
