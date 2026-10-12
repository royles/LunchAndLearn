import { useEffect, useRef, type KeyboardEvent, type MouseEvent } from "react";

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
  /** Only the sidebar row hosts the input; avoids duplicate fields for the active chat. */
  allowInlineEdit?: boolean;
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
  allowInlineEdit = true,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isEditing && allowInlineEdit) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [isEditing, allowInlineEdit, conversationId]);

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

  if (isEditing && allowInlineEdit) {
    return (
      <input
        ref={inputRef}
        type="text"
        className={`conv-title-input ${className}`.trim()}
        value={draft}
        maxLength={256}
        placeholder={placeholder}
        aria-label="Chat title"
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
      title={isHeader ? "Rename this chat" : "Open chat · double-click to rename"}
      onClick={() => {
        if (isHeader) {
          onStartEdit(conversationId);
          onChangeDraft(title);
        } else {
          onSelect?.(conversationId);
        }
      }}
      onDoubleClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        onStartEdit(conversationId);
        onChangeDraft(title);
      }}
    >
      {title}
    </button>
  );
}

/** Prevents blur on the title input before Edit / Delete click handlers run. */
export function preventBlurOnPointerDown(e: MouseEvent) {
  e.preventDefault();
}
