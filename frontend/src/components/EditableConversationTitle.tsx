import { useEffect, useRef, type KeyboardEvent } from "react";

type Props = {
  conversationId: number;
  title: string;
  isEditing: boolean;
  className?: string;
  placeholder?: string;
  onStartEdit: (conversationId: number) => void;
  onChangeDraft: (value: string) => void;
  onCommit: (conversationId: number, title: string) => void;
  onCancel: () => void;
  onSelect?: (conversationId: number) => void;
  draft: string;
};

export function EditableConversationTitle({
  conversationId,
  title,
  isEditing,
  className = "",
  placeholder = "Chat name",
  onStartEdit,
  onChangeDraft,
  onCommit,
  onCancel,
  onSelect,
  draft,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isEditing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [isEditing, conversationId]);

  function commit() {
    const trimmed = draft.trim() || "New chat";
    onCommit(conversationId, trimmed);
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      commit();
    } else if (e.key === "Escape") {
      e.preventDefault();
      onCancel();
    }
  }

  if (isEditing) {
    return (
      <input
        ref={inputRef}
        type="text"
        className={`conv-title-input ${className}`.trim()}
        value={draft}
        maxLength={256}
        placeholder={placeholder}
        onChange={(e) => onChangeDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={onKeyDown}
        onClick={(e) => e.stopPropagation()}
      />
    );
  }

  const isHeader = className.includes("main-title");

  return (
    <button
      type="button"
      className={`conv-title ${className}`.trim()}
      title="Double-click to rename"
      onClick={() => {
        if (!isHeader) onSelect?.(conversationId);
      }}
      onDoubleClick={(e) => {
        e.preventDefault();
        onStartEdit(conversationId);
        onChangeDraft(title);
      }}
    >
      {title}
    </button>
  );
}
