import { useCallback, useEffect, useState } from "react";
import {
  createConversation,
  deleteConversation,
  fetchModelSettings,
  listConversations,
  listMessages,
  renameConversation,
  streamChat,
  type Conversation,
  type ImageAttachment,
  type Message,
  type ModelSettingsPublic,
} from "./api/client";
import { ChatComposer } from "./components/ChatComposer";
import { EditableConversationTitle } from "./components/EditableConversationTitle";
import { MessageBubble } from "./components/MessageBubble";
import { ModelSettingsPanel } from "./components/ModelSettingsPanel";

export default function App() {
  const [modelSettings, setModelSettings] = useState<ModelSettingsPublic | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingText, setStreamingText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [titleDraft, setTitleDraft] = useState("");

  const refreshConversations = useCallback(async () => {
    const list = await listConversations();
    setConversations(list);
    return list;
  }, []);

  useEffect(() => {
    (async () => {
      try {
        setModelSettings(await fetchModelSettings());
        const list = await refreshConversations();
        if (list.length === 0) {
          const created = await createConversation();
          setConversations([created]);
          setActiveId(created.id);
          setEditingId(created.id);
          setTitleDraft(created.title);
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

  async function commitTitle(conversationId: number, title: string) {
    setEditingId(null);
    const previous = conversations.find((c) => c.id === conversationId)?.title;
    if (previous === title) return;
    setConversations((prev) =>
      prev.map((c) => (c.id === conversationId ? { ...c, title } : c)),
    );
    try {
      const updated = await renameConversation(conversationId, title);
      setConversations((prev) =>
        prev.map((c) => (c.id === conversationId ? updated : c)),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to rename chat");
      if (previous != null) {
        setConversations((prev) =>
          prev.map((c) => (c.id === conversationId ? { ...c, title: previous } : c)),
        );
      }
    }
  }

  function startEditing(conversationId: number) {
    const conv = conversations.find((c) => c.id === conversationId);
    if (!conv) return;
    setEditingId(conversationId);
    setTitleDraft(conv.title);
  }

  async function handleNewChat() {
    const conv = await createConversation();
    setConversations((prev) => [conv, ...prev]);
    setActiveId(conv.id);
    setMessages([]);
    setStreamingText("");
    setEditingId(conv.id);
    setTitleDraft(conv.title);
  }

  async function handleDelete(id: number) {
    await deleteConversation(id);
    if (editingId === id) setEditingId(null);
    const list = await refreshConversations();
    if (activeId === id) {
      if (list.length === 0) {
        const conv = await createConversation();
        setConversations([conv]);
        setActiveId(conv.id);
        setMessages([]);
        setEditingId(conv.id);
        setTitleDraft(conv.title);
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

  const activeConversation = conversations.find((c) => c.id === activeId);

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
        <div className="sidebar-actions">
          <button type="button" className="new-chat-btn" onClick={handleNewChat}>
            + New chat
          </button>
          <button
            type="button"
            className="settings-btn"
            onClick={() => setSettingsOpen(true)}
            title="Model settings"
          >
            Model
          </button>
        </div>
        <nav className="conv-list">
          {conversations.map((c) => (
            <div
              key={c.id}
              className={`conv-item ${c.id === activeId ? "active" : ""}`}
            >
              <EditableConversationTitle
                conversationId={c.id}
                title={c.title}
                isEditing={editingId === c.id}
                draft={editingId === c.id ? titleDraft : c.title}
                onStartEdit={startEditing}
                onChangeDraft={setTitleDraft}
                onCommit={commitTitle}
                onCancel={() => setEditingId(null)}
                onSelect={setActiveId}
              />
              <button
                type="button"
                className="conv-rename"
                title="Rename"
                onClick={() => startEditing(c.id)}
              >
                Edit
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
        {modelSettings && (
          <footer className="sidebar-footer">
            <span className="mono">{modelSettings.model_id}</span>
            <span className="muted truncate">{modelSettings.model_endpoint_url}</span>
            {modelSettings.has_model_token && (
              <span className="muted">Token {modelSettings.model_token_masked}</span>
            )}
          </footer>
        )}
      </aside>

      <ModelSettingsPanel
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onSaved={setModelSettings}
      />

      <main className="main">
        <header className="main-header">
          {activeConversation ? (
            <EditableConversationTitle
              conversationId={activeConversation.id}
              title={activeConversation.title}
              isEditing={editingId === activeConversation.id}
              draft={editingId === activeConversation.id ? titleDraft : activeConversation.title}
              className="main-title"
              onStartEdit={startEditing}
              onChangeDraft={setTitleDraft}
              onCommit={commitTitle}
              onCancel={() => setEditingId(null)}
            />
          ) : (
            <h2>Chat</h2>
          )}
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
