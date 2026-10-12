import { useEffect, useState, type FormEvent } from "react";
import {
  fetchModelSettings,
  saveModelSettings,
  type ModelSettingsPublic,
} from "../api/client";

type Props = {
  open: boolean;
  onClose: () => void;
  onSaved: (settings: ModelSettingsPublic) => void;
};

export function ModelSettingsPanel({ open, onClose, onSaved }: Props) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [endpoint, setEndpoint] = useState("");
  const [modelId, setModelId] = useState("");
  const [tokenInput, setTokenInput] = useState("");
  const [masked, setMasked] = useState<string | null>(null);
  const [hasToken, setHasToken] = useState(false);

  useEffect(() => {
    if (!open) return;
    (async () => {
      setLoading(true);
      setError(null);
      setTokenInput("");
      try {
        const s = await fetchModelSettings();
        setEndpoint(s.model_endpoint_url);
        setModelId(s.model_id);
        setMasked(s.model_token_masked);
        setHasToken(s.has_model_token);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load settings");
      } finally {
        setLoading(false);
      }
    })();
  }, [open]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const saved = await saveModelSettings({
        model_endpoint_url: endpoint.trim(),
        model_id: modelId.trim(),
        model_token: tokenInput === "" ? undefined : tokenInput,
      });
      setMasked(saved.model_token_masked);
      setHasToken(saved.has_model_token);
      setTokenInput("");
      onSaved(saved);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  async function clearToken() {
    setSaving(true);
    setError(null);
    try {
      const saved = await saveModelSettings({
        model_endpoint_url: endpoint.trim(),
        model_id: modelId.trim(),
        model_token: "",
      });
      setMasked(saved.model_token_masked);
      setHasToken(saved.has_model_token);
      setTokenInput("");
      onSaved(saved);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to clear token");
    } finally {
      setSaving(false);
    }
  }

  if (!open) return null;

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="modal"
        role="dialog"
        aria-labelledby="model-settings-title"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="modal-header">
          <h2 id="model-settings-title">Model connection</h2>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>

        {loading ? (
          <p className="muted">Loading…</p>
        ) : (
          <form className="settings-form" onSubmit={onSubmit}>
            <label>
              Endpoint URL
              <input
                type="url"
                value={endpoint}
                onChange={(e) => setEndpoint(e.target.value)}
                placeholder="http://127.0.0.1:11434/v1"
                required
              />
            </label>
            <label>
              Model ID
              <input
                type="text"
                value={modelId}
                onChange={(e) => setModelId(e.target.value)}
                placeholder="llama3.2"
                required
              />
            </label>
            <label>
              Model token
              <input
                type="password"
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                placeholder={
                  hasToken
                    ? "Enter new token to replace, or leave blank to keep saved token"
                    : "API token (optional for local servers)"
                }
                autoComplete="new-password"
              />
            </label>
            {hasToken && (
              <p className="token-mask-line">
                Saved token: <span className="mono">{masked ?? "••••••••••••"}</span>
              </p>
            )}
            {hasToken && (
              <button type="button" className="link-btn" onClick={clearToken} disabled={saving}>
                Remove saved token
              </button>
            )}
            {error && <p className="form-error">{error}</p>}
            <div className="modal-actions">
              <button type="button" className="ghost-btn" onClick={onClose}>
                Cancel
              </button>
              <button type="submit" className="send-btn" disabled={saving}>
                {saving ? "Saving…" : "Save"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
