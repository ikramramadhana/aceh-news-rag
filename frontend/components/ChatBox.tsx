"use client";

import Link from "next/link";
import { useState, useRef, useEffect, useCallback } from "react";

type Source = {
  title: string;
  url: string;
  published_at: string;
};

type Message = {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  suggestions?: string[];
  feedback?: "like" | "dislike";
  questionFor?: string; // pertanyaan yang memicu jawaban ini, buat dikirim ke /feedback
};

type Conversation = {
  id: string;
  title: string;
  messages: Message[];
  updatedAt: number;
};

type Category = { category: string; article_count: number };
type LatestArticle = { id_wp: number; title: string; url: string; published_at: string };

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const STORAGE_KEY = "aceh-hari-ini-chat"; // format lama (satu percakapan)
const CONVERSATIONS_KEY = "aceh-hari-ini-conversations"; // format baru (banyak percakapan)

const EXAMPLE_QUESTIONS = [
  "Mualem ngomong apa soal pertanahan?",
  "Berita terbaru soal APBA",
  "Perkembangan penanganan banjir Aceh",
  "Apa saja program unggulan Pemerintah Aceh?",
];

function nextDayISO(dateStr: string): string {
  const d = new Date(`${dateStr}T00:00:00`);
  d.setDate(d.getDate() + 1);
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}T00:00:00`;
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("id-ID", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

function groupLabel(ts: number): string {
  const d = new Date(ts);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);
  if (d.toDateString() === today.toDateString()) return "Hari ini";
  if (d.toDateString() === yesterday.toDateString()) return "Kemarin";
  return d.toLocaleDateString("id-ID", { day: "numeric", month: "long" });
}

function newId(): string {
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 7)}`;
}

function Icon({ d, size = 16 }: { d: string; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={d} />
    </svg>
  );
}

const ICONS = {
  plus: "M12 5v14M5 12h14",
  menu: "M4 6h16M4 12h16M4 18h16",
  close: "M18 6 6 18M6 6l12 12",
  send: "m22 2-7 20-4-9-9-4 20-7Z",
  trash: "M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6",
  up: "M7 10v12M15 5.9 14 10h5.8a2 2 0 0 1 1.9 2.5l-2.3 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.8a2 2 0 0 0 1.8-1.1L12 2a3.1 3.1 0 0 1 3 3.9Z",
  down: "M17 14V2M9 18.1 10 14H4.2a2 2 0 0 1-1.9-2.5l2.3-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.8a2 2 0 0 0-1.8 1.1L12 22a3.1 3.1 0 0 1-3-3.9Z",
  info: "M12 16v-4M12 8h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z",
  home: "m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1V10Z",
};

export default function ChatBox() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategory, setSelectedCategory] = useState("");
  const [selectedDate, setSelectedDate] = useState("");
  const [showLatest, setShowLatest] = useState(false);
  const [latestArticles, setLatestArticles] = useState<LatestArticle[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const active = conversations.find((c) => c.id === activeId) || null;
  const messages: Message[] = active ? active.messages : [];

  useEffect(() => {
    fetch(`${API_URL}/articles/latest?limit=6`)
      .then((res) => res.json())
      .then((data) => setLatestArticles(data))
      .catch(() => setLatestArticles([]));
  }, []);

  useEffect(() => {
    fetch(`${API_URL}/categories`)
      .then((res) => res.json())
      .then((data) => setCategories(data))
      .catch(() => setCategories([]));
  }, []);

  // muat riwayat; migrasi percakapan format lama kalau ada
  useEffect(() => {
    try {
      const saved = localStorage.getItem(CONVERSATIONS_KEY);
      if (saved) {
        const parsed: Conversation[] = JSON.parse(saved);
        setConversations(parsed);
      } else {
        const old = localStorage.getItem(STORAGE_KEY);
        if (old) {
          const oldMessages: Message[] = JSON.parse(old);
          if (oldMessages.length > 0) {
            const firstUser = oldMessages.find((m) => m.role === "user");
            setConversations([
              {
                id: newId(),
                title: (firstUser?.content || "Percakapan lama").slice(0, 40),
                messages: oldMessages,
                updatedAt: Date.now(),
              },
            ]);
          }
          localStorage.removeItem(STORAGE_KEY);
        }
      }
    } catch {
      // abaikan
    }
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    try {
      localStorage.setItem(CONVERSATIONS_KEY, JSON.stringify(conversations));
    } catch {
      // abaikan
    }
  }, [conversations, hydrated]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const updateMessages = useCallback(
    (id: string, fn: (prev: Message[]) => Message[]) => {
      setConversations((prev) =>
        prev.map((c) => (c.id === id ? { ...c, messages: fn(c.messages), updatedAt: Date.now() } : c))
      );
    },
    []
  );

  function startNewConversation() {
    if (loading) return;
    setActiveId(null);
    setInput("");
    setSidebarOpen(false);
  }

  function openConversation(id: string) {
    if (loading) return;
    setActiveId(id);
    setSidebarOpen(false);
  }

  function deleteConversation(id: string) {
    if (loading) return;
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (activeId === id) setActiveId(null);
  }

  async function sendQuestion(question: string) {
    if (!question.trim() || loading) return;

    // ambil beberapa pesan terakhir sebagai konteks (sebelum pesan baru ditambahkan)
    const history = messages
      .filter((m) => m.content.trim().length > 0)
      .slice(-6)
      .map((m) => ({ role: m.role, content: m.content }));

    // buat percakapan baru kalau belum ada yang aktif
    let convId = activeId;
    if (!convId) {
      convId = newId();
      const created: Conversation = {
        id: convId,
        title: question.trim().slice(0, 40),
        messages: [],
        updatedAt: Date.now(),
      };
      setConversations((prev) => [created, ...prev]);
      setActiveId(convId);
    }
    const id = convId;

    updateMessages(id, (prev) => [
      ...prev,
      { role: "user", content: question },
      { role: "assistant", content: "", questionFor: question },
    ]);
    setInput("");
    setLoading(true);

    const patchLast = (patch: (last: Message) => Message) =>
      updateMessages(id, (prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = patch(updated[updated.length - 1]);
        return updated;
      });

    try {
      const res = await fetch(`${API_URL}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          filter_category: selectedCategory || null,
          // date picker = filter satu hari penuh (bukan "sejak tanggal ini"),
          // jadi kirim batas bawah & atas (besoknya, eksklusif)
          filter_after: selectedDate ? `${selectedDate}T00:00:00` : null,
          filter_before: selectedDate ? nextDayISO(selectedDate) : null,
          history,
        }),
      });

      if (res.status === 429) {
        throw new Error("RATE_LIMIT");
      }
      if (!res.ok || !res.body) throw new Error(`Server error: ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const rawEvent of events) {
          const lines = rawEvent.split("\n");
          const eventType = lines
            .find((l) => l.startsWith("event: "))
            ?.replace("event: ", "");
          const dataLine = lines.find((l) => l.startsWith("data: "));
          if (!eventType || !dataLine) continue;

          const data = JSON.parse(dataLine.replace("data: ", ""));

          if (eventType === "sources") {
            patchLast((last) => ({ ...last, sources: data }));
          } else if (eventType === "suggestions") {
            patchLast((last) => ({ ...last, suggestions: data }));
          } else if (eventType === "answer") {
            patchLast((last) => ({ ...last, content: last.content + data.text }));
          }
        }
      }
    } catch (err) {
      const isRateLimit = err instanceof Error && err.message === "RATE_LIMIT";
      patchLast(() => ({
        role: "assistant",
        content: isRateLimit
          ? "Kamu udah nanya cukup banyak dalam waktu singkat. Istirahat sebentar ya, coba lagi beberapa menit lagi."
          : "Waduh, ada kendala menghubungi server. Pastikan backend-nya lagi jalan ya, terus coba lagi.",
      }));
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendQuestion(input);
    }
  }

  async function submitFeedback(index: number, rating: "like" | "dislike") {
    const target = messages[index];
    if (!target || target.feedback || !activeId) return; // sudah pernah kasih feedback

    updateMessages(activeId, (prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], feedback: rating };
      return updated;
    });

    try {
      await fetch(`${API_URL}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: target.questionFor || "",
          answer: target.content,
          rating,
        }),
      });
    } catch {
      // gagal kirim feedback, biarkan aja - nggak kritis buat UX
    }
  }

  // kelompokkan riwayat berdasarkan hari
  const sorted = [...conversations].sort((a, b) => b.updatedAt - a.updatedAt);
  const groups: { label: string; items: Conversation[] }[] = [];
  for (const c of sorted) {
    const label = groupLabel(c.updatedAt);
    const g = groups.find((x) => x.label === label);
    if (g) g.items.push(c);
    else groups.push({ label, items: [c] });
  }

  const hasFilter = !!(selectedCategory || selectedDate);

  const sidebar = (
    <aside
      className="h-full w-72 flex flex-col border-r"
      style={{ background: "var(--d-surface)", borderColor: "var(--d-line)" }}
    >
      <div className="flex items-center justify-between px-4 pt-4 pb-3">
        <div className="flex items-center gap-2.5">
          <img src="/logo.png" alt="Logo Pancacita Aceh" className="w-7 h-7 object-contain" />
          <span className="font-display font-bold">Aceh Hari Ini</span>
        </div>
        <button
          onClick={() => setSidebarOpen(false)}
          className="lg:hidden p-1.5 rounded-md"
          style={{ color: "var(--d-muted)" }}
          aria-label="Tutup menu"
        >
          <Icon d={ICONS.close} />
        </button>
      </div>

      <div className="px-3 pb-3">
        <button
          onClick={startNewConversation}
          className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg text-sm font-semibold"
          style={{ background: "var(--d-accent)", color: "#06130e" }}
        >
          <Icon d={ICONS.plus} size={15} />
          Percakapan Baru
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 pb-3">
        <p className="px-1 pt-2 pb-1.5 text-xs font-semibold" style={{ color: "var(--d-muted)" }}>
          Riwayat Chat
        </p>
        {groups.length === 0 ? (
          <p className="px-1 text-xs" style={{ color: "var(--d-muted)" }}>
            Belum ada percakapan.
          </p>
        ) : (
          groups.map((g) => (
            <div key={g.label} className="mb-2">
              <p className="px-1 py-1 text-[11px]" style={{ color: "var(--d-muted)" }}>
                {g.label}
              </p>
              {g.items.map((c) => (
                <div
                  key={c.id}
                  className="group flex items-center rounded-lg"
                  style={{ background: c.id === activeId ? "var(--d-surface-2)" : "transparent" }}
                >
                  <button
                    onClick={() => openConversation(c.id)}
                    className="flex-1 min-w-0 text-left text-sm px-2.5 py-2 truncate"
                    style={{ color: c.id === activeId ? "var(--d-ink)" : "var(--d-muted)" }}
                  >
                    {c.title}
                  </button>
                  <button
                    onClick={() => deleteConversation(c.id)}
                    className="p-2 opacity-0 group-hover:opacity-100 focus:opacity-100 lg:opacity-0"
                    style={{ color: "var(--d-muted)" }}
                    aria-label="Hapus percakapan"
                  >
                    <Icon d={ICONS.trash} size={14} />
                  </button>
                </div>
              ))}
            </div>
          ))
        )}

        <p className="px-1 pt-4 pb-2 text-xs font-semibold" style={{ color: "var(--d-muted)" }}>
          Filter Berita
        </p>
        <div className="space-y-2">
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="w-full text-xs px-3 py-2 rounded-lg focus:outline-none"
            style={{ border: "1px solid var(--d-line)", color: "var(--d-ink)", background: "var(--d-surface-2)" }}
          >
            <option value="">Semua kategori</option>
            {categories.map((c) => (
              <option key={c.category} value={c.category}>
                {c.category} ({c.article_count})
              </option>
            ))}
          </select>
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="w-full text-xs px-3 py-2 rounded-lg focus:outline-none"
            style={{ border: "1px solid var(--d-line)", color: "var(--d-ink)", background: "var(--d-surface-2)" }}
          />
          {hasFilter && (
            <button
              onClick={() => {
                setSelectedCategory("");
                setSelectedDate("");
              }}
              className="text-xs font-medium"
              style={{ color: "var(--d-accent-2)" }}
            >
              Reset filter
            </button>
          )}
        </div>

        <button
          onClick={() => setShowLatest((v) => !v)}
          className="w-full flex items-center justify-between px-1 pt-4 pb-2 text-xs font-semibold"
          style={{ color: "var(--d-muted)" }}
        >
          Berita Terkini
          <span>{showLatest ? "−" : "+"}</span>
        </button>
        {showLatest &&
          (latestArticles.length === 0 ? (
            <p className="px-1 text-xs" style={{ color: "var(--d-muted)" }}>
              Memuat...
            </p>
          ) : (
            <ul className="space-y-1.5">
              {latestArticles.map((a) => (
                <li key={a.id_wp}>
                  <a
                    href={a.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block px-2.5 py-2 rounded-lg text-xs hover:brightness-125"
                    style={{ background: "var(--d-surface-2)" }}
                  >
                    <span className="line-clamp-2" style={{ color: "var(--d-ink)" }}>
                      {a.title}
                    </span>
                    <span className="block mt-0.5" style={{ color: "var(--d-muted)" }}>
                      {formatDate(a.published_at)}
                    </span>
                  </a>
                </li>
              ))}
            </ul>
          ))}
      </div>

      <div className="p-3 border-t" style={{ borderColor: "var(--d-line)" }}>
        <Link
          href="/"
          className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg text-sm font-semibold"
          style={{ background: "var(--d-surface-2)", color: "var(--d-ink)" }}
        >
          <Icon d={ICONS.home} size={15} />
          Kembali ke Beranda
        </Link>
      </div>
    </aside>
  );

  return (
    <div className="dark-theme flex h-dvh overflow-hidden">
      {/* Sidebar desktop */}
      <div className="hidden lg:block shrink-0">{sidebar}</div>

      {/* Sidebar mobile (drawer) */}
      {sidebarOpen && (
        <div className="lg:hidden fixed inset-0 z-40 flex">
          <div className="h-full">{sidebar}</div>
          <button
            className="flex-1"
            style={{ background: "rgba(0,0,0,0.6)" }}
            onClick={() => setSidebarOpen(false)}
            aria-label="Tutup menu"
          />
        </div>
      )}

      <div className="flex-1 min-w-0 flex flex-col">
        {/* Top bar mobile */}
        <div
          className="lg:hidden shrink-0 flex items-center gap-3 px-4 py-3 border-b"
          style={{ borderColor: "var(--d-line)" }}
        >
          <button onClick={() => setSidebarOpen(true)} aria-label="Buka menu" style={{ color: "var(--d-ink)" }}>
            <Icon d={ICONS.menu} size={20} />
          </button>
          <span className="font-display font-bold text-sm">Aceh Hari Ini</span>
          {hasFilter && (
            <span
              className="ml-auto text-[11px] px-2 py-1 rounded-full"
              style={{ background: "var(--d-accent-soft)", color: "var(--d-accent)" }}
            >
              Filter aktif
            </span>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 space-y-5">
            {messages.length === 0 && (
              <div className="pt-6 sm:pt-12">
                <div className="text-center mb-8">
                  <img src="/logo.png" alt="Logo Pancacita Aceh" className="w-14 h-14 object-contain mx-auto mb-4" />
                  <h2 className="font-display font-bold text-2xl mb-2">
                    Selamat Datang di <span style={{ color: "var(--d-accent)" }}>Aceh Hari Ini</span>
                  </h2>
                  <p className="text-sm" style={{ color: "var(--d-muted)" }}>
                    Tanyakan seputar berita Pemerintah Aceh, atau pilih contoh di bawah.
                  </p>
                </div>

                <div className="grid gap-2.5 mb-6">
                  {EXAMPLE_QUESTIONS.map((q) => (
                    <button
                      key={q}
                      onClick={() => sendQuestion(q)}
                      className="text-left text-sm px-4 py-3 rounded-xl border transition-colors hover:border-[color:var(--d-accent)]"
                      style={{ borderColor: "var(--d-line)", background: "var(--d-surface)" }}
                    >
                      {q}
                    </button>
                  ))}
                </div>

                <div
                  className="rounded-2xl border p-5"
                  style={{ borderColor: "rgba(31,197,142,0.25)", background: "var(--d-accent-soft)" }}
                >
                  <div className="flex items-center gap-2 mb-2.5" style={{ color: "var(--d-accent)" }}>
                    <Icon d={ICONS.info} size={18} />
                    <span className="font-display font-bold text-sm">Fokus Berita Pemerintahan Aceh</span>
                  </div>
                  <ul className="text-xs space-y-1.5 list-disc pl-5" style={{ color: "var(--d-muted)" }}>
                    <li>Hanya menjawab dari berita resmi humas.acehprov.go.id.</li>
                    <li>Setiap jawaban disertai sumber berita yang dipakai.</li>
                    <li>Pertanyaan di luar cakupan berita tidak akan dijawab dengan mengarang.</li>
                  </ul>
                </div>
              </div>
            )}

            {messages.map((m, i) =>
              m.role === "user" ? (
                <div key={i} className="flex justify-end">
                  <div
                    className="max-w-[85%] sm:max-w-[75%] px-4 py-2.5 text-sm rounded-2xl rounded-br-md font-medium"
                    style={{ background: "var(--d-accent)", color: "#06130e" }}
                  >
                    {m.content}
                  </div>
                </div>
              ) : (
                <div key={i} className="flex justify-start gap-3">
                  <div
                    className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-0.5 p-1.5"
                    style={{ background: "var(--d-surface-2)", border: "1px solid var(--d-line)" }}
                  >
                    <img src="/logo.png" alt="Logo Pancacita Aceh" className="w-full h-full object-contain" />
                  </div>
                  <div
                    className="max-w-[88%] sm:max-w-[82%] px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap rounded-2xl rounded-tl-md"
                    style={{
                      background: "var(--d-surface)",
                      border: "1px solid var(--d-line)",
                      color: m.content ? "var(--d-ink)" : "var(--d-muted)",
                    }}
                  >
                    {m.content || (loading && i === messages.length - 1 ? "Lagi nyari beritanya..." : "")}

                    {m.sources && m.sources.length > 0 && (
                      <div className="mt-3 pt-3" style={{ borderTop: "1px solid var(--d-line)" }}>
                        <p className="text-xs mb-2 font-semibold" style={{ color: "var(--d-accent)" }}>
                          Sumber ({m.sources.length})
                        </p>
                        <ul className="space-y-2">
                          {m.sources.map((s, j) => (
                            <li key={j}>
                              <a
                                href={s.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs block hover:underline"
                                style={{ color: "var(--d-ink)" }}
                              >
                                {s.title}
                              </a>
                              <span className="text-xs" style={{ color: "var(--d-muted)" }}>
                                {formatDate(s.published_at)}
                              </span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {m.suggestions && m.suggestions.length > 0 && (
                      <div className="mt-3 pt-3" style={{ borderTop: "1px solid var(--d-line)" }}>
                        <div className="flex flex-col gap-1.5">
                          {m.suggestions.map((s, j) => (
                            <button
                              key={j}
                              onClick={() => sendQuestion(s)}
                              disabled={loading}
                              className="text-left text-xs px-3 py-2 rounded-lg transition-colors disabled:opacity-50 hover:border-[color:var(--d-accent)]"
                              style={{
                                background: "var(--d-surface-2)",
                                color: "var(--d-ink)",
                                border: "1px solid var(--d-line)",
                              }}
                            >
                              {s}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {m.content && !loading && (
                      <div className="mt-3 pt-1 flex items-center gap-1.5">
                        <button
                          onClick={() => submitFeedback(i, "like")}
                          disabled={!!m.feedback}
                          className="p-1.5 rounded-md transition-opacity disabled:cursor-default"
                          style={{
                            opacity: !m.feedback || m.feedback === "like" ? 1 : 0.3,
                            background: m.feedback === "like" ? "var(--d-accent)" : "transparent",
                            color: m.feedback === "like" ? "#06130e" : "var(--d-muted)",
                          }}
                          title="Jawaban membantu"
                          aria-label="Jawaban membantu"
                        >
                          <Icon d={ICONS.up} size={15} />
                        </button>
                        <button
                          onClick={() => submitFeedback(i, "dislike")}
                          disabled={!!m.feedback}
                          className="p-1.5 rounded-md transition-opacity disabled:cursor-default"
                          style={{
                            opacity: !m.feedback || m.feedback === "dislike" ? 1 : 0.3,
                            background: m.feedback === "dislike" ? "var(--d-accent-2)" : "transparent",
                            color: m.feedback === "dislike" ? "#1a1400" : "var(--d-muted)",
                          }}
                          title="Jawaban kurang membantu"
                          aria-label="Jawaban kurang membantu"
                        >
                          <Icon d={ICONS.down} size={15} />
                        </button>
                        {m.feedback && (
                          <span className="text-xs ml-1" style={{ color: "var(--d-muted)" }}>
                            Makasih atas masukannya!
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )
            )}

            <div ref={bottomRef} />
          </div>
        </div>

        {/* Input */}
        <div className="shrink-0 px-4 sm:px-6 pb-4 pt-2">
          <div
            className="max-w-3xl mx-auto flex items-end gap-2 rounded-2xl border px-3 py-2"
            style={{ borderColor: "var(--d-line)", background: "var(--d-surface)" }}
          >
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Tanyakan sesuatu tentang berita Pemerintah Aceh..."
              rows={1}
              className="flex-1 resize-none bg-transparent px-2 py-2 text-sm focus:outline-none max-h-32"
              style={{ color: "var(--d-ink)" }}
            />
            <button
              onClick={() => sendQuestion(input)}
              disabled={loading || !input.trim()}
              className="shrink-0 w-9 h-9 rounded-xl flex items-center justify-center disabled:opacity-40 transition-opacity"
              style={{ background: "var(--d-accent)", color: "#06130e" }}
              aria-label="Kirim"
            >
              <Icon d={ICONS.send} size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
