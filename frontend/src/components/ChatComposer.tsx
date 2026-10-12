import { useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import type { ImageAttachment } from "../api/client";
import { fileToAttachment } from "../api/client";

type Props = {
  disabled: boolean;
  onSend: (text: string, images: ImageAttachment[]) => void;
};

export function ChatComposer({ disabled, onSend }: Props) {
  const [text, setText] = useState("");
  const [attachments, setAttachments] = useState<ImageAttachment[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);

  async function onPickFiles(files: FileList | null) {
    if (!files?.length) return;
    const nextAtt: ImageAttachment[] = [];
    const nextPrev: string[] = [];
    for (const file of Array.from(files)) {
      if (!file.type.startsWith("image/")) continue;
      const att = await fileToAttachment(file);
      nextAtt.push(att);
      nextPrev.push(`data:${att.mime_type};base64,${att.data}`);
    }
    setAttachments((prev) => [...prev, ...nextAtt]);
    setPreviews((prev) => [...prev, ...nextPrev]);
  }

  function submit(e?: FormEvent) {
    e?.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed, attachments);
    setText("");
    setAttachments([]);
    setPreviews([]);
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <form className="composer" onSubmit={submit}>
      {previews.length > 0 && (
        <div className="composer-previews">
          {previews.map((src, i) => (
            <img key={i} src={src} alt="" />
          ))}
        </div>
      )}
      <div className="composer-row">
        <button
          type="button"
          className="icon-btn"
          title="Attach image"
          disabled={disabled}
          onClick={() => fileRef.current?.click()}
        >
          +
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          multiple
          hidden
          onChange={(e) => onPickFiles(e.target.files)}
        />
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Message your local model… (Enter to send, Shift+Enter for newline)"
          rows={1}
          disabled={disabled}
        />
        <button type="submit" className="send-btn" disabled={disabled || !text.trim()}>
          Send
        </button>
      </div>
      <p className="composer-hint">Supports vision models via OpenAI-compatible multimodal messages.</p>
    </form>
  );
}
