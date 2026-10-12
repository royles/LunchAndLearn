import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { MessageContent } from "../api/client";

type Props = {
  role: "user" | "assistant" | "system";
  content: MessageContent;
  streaming?: boolean;
};

function extractParts(content: MessageContent) {
  if (typeof content === "string") {
    return { text: content, images: [] as string[] };
  }
  const textParts: string[] = [];
  const images: string[] = [];
  for (const part of content) {
    if (part.type === "text" && part.text) textParts.push(part.text);
    if (part.type === "image_url" && part.image_url?.url) images.push(part.image_url.url);
  }
  return { text: textParts.join("\n"), images };
}

export function MessageBubble({ role, content, streaming }: Props) {
  const { text, images } = extractParts(content);
  const isUser = role === "user";

  return (
    <article className={`bubble ${isUser ? "bubble-user" : "bubble-assistant"}`}>
      <header className="bubble-role">{isUser ? "You" : "Assistant"}</header>
      {images.length > 0 && (
        <div className="bubble-images">
          {images.map((src, i) => (
            <img key={i} src={src} alt="" className="bubble-image" />
          ))}
        </div>
      )}
      <div className={`bubble-body ${streaming ? "streaming" : ""}`}>
        {isUser ? (
          <p className="plain-text">{text}</p>
        ) : (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{text || (streaming ? "▍" : "")}</ReactMarkdown>
        )}
      </div>
    </article>
  );
}
