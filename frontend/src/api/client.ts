export type ImageAttachment = {
  mime_type: string;
  data: string;
};

export type MessageContent =
  | string
  | Array<{ type: string; text?: string; image_url?: { url: string } }>;

export type Message = {
  id: number;
  conversation_id: number;
  role: "user" | "assistant" | "system";
  content: MessageContent;
  created_at: string;
};

export type Conversation = {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
};

export type PublicConfig = {
  llm_base_url: string;
  llm_model: string;
  supports_multimodal: boolean;
  supports_streaming: boolean;
};

async function parseJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export async function fetchConfig(): Promise<PublicConfig> {
  return parseJson(await fetch("/api/v1/config"));
}

export async function listConversations(): Promise<Conversation[]> {
  return parseJson(await fetch("/api/v1/conversations"));
}

export async function createConversation(title = "New chat"): Promise<Conversation> {
  return parseJson(
    await fetch("/api/v1/conversations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    }),
  );
}

export async function deleteConversation(id: number): Promise<void> {
  const res = await fetch(`/api/v1/conversations/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await res.text());
}

export async function listMessages(conversationId: number): Promise<Message[]> {
  return parseJson(await fetch(`/api/v1/conversations/${conversationId}/messages`));
}

export type StreamHandlers = {
  onToken: (token: string) => void;
  onDone: (message?: Message) => void;
  onError: (message: string) => void;
};

export async function streamChat(
  conversationId: number,
  message: string,
  images: ImageAttachment[],
  handlers: StreamHandlers,
  model?: string,
): Promise<void> {
  const res = await fetch(`/api/v1/conversations/${conversationId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, images, model: model || undefined }),
  });

  if (!res.ok || !res.body) {
    handlers.onError(await res.text());
    handlers.onDone();
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const raw = line.slice(6).trim();
      if (!raw) continue;
      try {
        const evt = JSON.parse(raw) as {
          type: string;
          content?: string;
          message?: string | Message;
        };
        if (evt.type === "token" && evt.content) handlers.onToken(evt.content);
        else if (evt.type === "error")
          handlers.onError(typeof evt.message === "string" ? evt.message : "Unknown error");
        else if (evt.type === "done")
          handlers.onDone(typeof evt.message === "object" ? evt.message : undefined);
      } catch {
        /* ignore malformed chunks */
      }
    }
  }
  handlers.onDone();
}

export function fileToAttachment(file: File): Promise<ImageAttachment> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      const base64 = result.split(",")[1];
      if (!base64) {
        reject(new Error("Failed to read image"));
        return;
      }
      resolve({ mime_type: file.type || "image/png", data: base64 });
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}
