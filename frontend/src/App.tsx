import { useCallback, useEffect, useState } from "react";
import {
  createConversation,
  deleteConversation,
  fetchConfig,
  listConversations,
  listMessages,
  streamChat,
  type Conversation,
  type ImageAttachment,
  type Message,
  type PublicConfig,
} from "./api/client";
import { ChatComposer } from "./components/ChatComposer";
import { MessageBubble } from "./components/MessageBubble";

export default function App() {
  const [config, setConfig] = useState<PublicConfig | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingText, setStreamingText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshConversations = useCallback(async () => {
    const list = await listConversations();
    setConversations(list);
    return list;
  }, []);

  useEffect(() => {
    (async () => {
      try {
        setConfig(await fetchConfig());
        const list = await refreshConversations();
        if (list.length === 0) {
          const created = await createConversation();
          setConversations([created]);
          setActiveId(created.id);
        } else {
          setActiveId(list[0].id);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load");
      }
    })();
  }, [refreshConversations]);

  useEffect(() => {
    if (activeId == null) return;
    (async () => {
      try {
        setMessages(await listMessages(activeId));
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load messages");
      }
    })();
  }, [activeId]);

  async function handleNewChat() {
    const conv = await createConversation();
    setConversations((prev) => [conv, ...prev]);
    setActiveId(conv.id);
    setMessages([]);
    setStreamingText("");
  }

  async function handleDelete(id: number) {
    await deleteConversation(id);
    const list = await refreshConversations();
    if (activeId === id) {
      if (list.length === 0) {
        const conv = await createConversation();
        setConversations([conv]);
        setActiveId(conv.id);
        setMessages([]);
      } else {
        setActiveId(list[0].id);
      }
    }
  }

  async function handleSend(text: string, images: ImageAttachment[]) {
    if (activeId == null) return;
    setError(null);
    setBusy(true);
    setStreamingText("");

    const userContent =
      images.length === 0
        ? text
        : [
            { type: "text", text },
            ...images.map((img) => ({
              type: "image_url" as const,
              image_url: { url: `data:${img.mime_type};base64,${img.data}` },
            })),
          ];

    const optimisticUser: Message = {
      id: -Date.now(),
      conversation_id: activeId,
      role: "user",
      content: userContent,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticUser]);

    await streamChat(activeId, text, images, {
      onToken: (token) => setStreamingText((prev) => prev + token),
      onError: (msg) => setError(msg),
      onDone: async (assistantMsg) => {
        setStreamingText("");
        setBusy(false);
        if (assistantMsg) {
          setMessages((prev) => [...prev.filter((m) => m.id !== optimisticUser.id), optimisticUser, assistantMsg]);
        } else {
          setMessages(await listMessages(activeId));
        }
        await refreshConversations();
      },
    });
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark" />
          <div>
            <h1>Local LLM</h1>
            <p className="brand-sub">OpenAI-compatible · streaming · vision</p>
          </div>
        </div>
        <button type="button" className="new-chat-btn" onClick={handleNewChat}>
          + New chat
        </button>
        <nav className="conv-list">
          {conversations.map((c) => (
            <div
              key={c.id}
              className={`conv-item ${c.id === activeId ? "active" : ""}`}
            >
              <button type="button" className="conv-title" onClick={() => setActiveId(c.id)}>
                {c.title}
              </button>
              <button
                type="button"
                className="conv-delete"
                title="Delete"
                onClick={() => handleDelete(c.id)}
              >
                ×
              </button>
            </div>
          ))}
        </nav>
        {config && (
          <footer className="sidebar-footer">
            <span className="mono">{config.llm_model}</span>
            <span className="muted truncate">{config.llm_base_url}</span>
          </footer>
        )}
      </aside>

      <main className="main">
        <header className="main-header">
          <h2>{conversations.find((c) => c.id === activeId)?.title ?? "Chat"}</h2>
        </header>

        {error && <div className="banner error">{error}</div>}

        <div className="thread">
          {messages.map((m) => (
            <MessageBubble key={m.id} role={m.role} content={m.content} />
          ))}
          {streamingText && (
            <MessageBubble role="assistant" content={streamingText} streaming />
          )}
        </div>

        <ChatComposer disabled={busy || activeId == null} onSend={handleSend} />
      </main>
    </div>
  );
}
