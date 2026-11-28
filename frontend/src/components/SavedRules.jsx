import React, { useEffect, useState } from "react";
import { listRules, saveRule, updateRule, deleteRule } from "../api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

/**
 * A user's saved rules, above the rule builder: load one, save the current
 * rule under a name, update or delete the loaded one.
 *
 * Mounted by the workspace (not by ConfigPanel itself) so the panel stays free
 * of the API layer and its Firebase import. If the list cannot be read — not
 * signed in, or an API without the route — the strip simply does not appear;
 * the builder works without it.
 */
export default function SavedRules({ rule, onLoad }) {
  const [rules, setRules] = useState(null);
  const [max, setMax] = useState(20);
  const [picked, setPicked] = useState("");
  const [naming, setNaming] = useState(false);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState(null);

  async function refresh() {
    try {
      const data = await listRules();
      setRules(data.rules);
      setMax(data.max);
      return data.rules;
    } catch {
      setRules(null);
      return null;
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  if (rules === null) return null;

  const current = rules.find((r) => r.id === picked) || null;

  async function act(fn, done) {
    setBusy(true);
    setNote(null);
    try {
      await fn();
      setNote({ tone: "text-gain", text: done });
    } catch (err) {
      setNote({ tone: "text-loss", text: err.message || "That did not work." });
    } finally {
      setBusy(false);
    }
  }

  function handlePick(id) {
    setPicked(id);
    setNote(null);
    const r = rules.find((x) => x.id === id);
    if (r) onLoad(r.rule);
  }

  function handleSave(e) {
    e.preventDefault();
    act(async () => {
      const saved = await saveRule(name, rule);
      await refresh();
      setPicked(saved.id);
      setNaming(false);
      setName("");
    }, `Saved as “${name.trim()}”.`);
  }

  return (
    <div className="rounded-md border border-border bg-muted/30 p-3 flex flex-col gap-2" data-testid="saved-rules">
      <div className="flex flex-wrap items-center gap-2">
        <select
          aria-label="Saved rules"
          value={picked}
          onChange={(e) => handlePick(e.target.value)}
          className="h-8 rounded-md border border-border bg-background px-2 text-sm text-foreground flex-1 min-w-0"
        >
          <option value="">{rules.length ? "Load a saved rule…" : "No saved rules yet"}</option>
          {rules.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>
        {!naming && (
          <Button type="button" variant="ghost" size="sm" disabled={busy || rules.length >= max} onClick={() => setNaming(true)}>
            Save as…
          </Button>
        )}
      </div>

      {naming && (
        <form onSubmit={handleSave} className="flex items-center gap-2">
          <Input
            aria-label="Rule name"
            autoFocus
            maxLength={60}
            value={name}
            placeholder="e.g. RSI dip in an uptrend"
            onChange={(e) => setName(e.target.value)}
            className="h-8 text-sm"
          />
          <Button type="submit" size="sm" disabled={busy || !name.trim()}>
            Save
          </Button>
          <Button type="button" variant="ghost" size="sm" onClick={() => setNaming(false)}>
            Cancel
          </Button>
        </form>
      )}

      {current && !naming && (
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={busy}
            onClick={() => act(async () => { await updateRule(current.id, { rule }); await refresh(); }, `Updated “${current.name}”.`)}
          >
            Update “{current.name}”
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="text-loss"
            disabled={busy}
            onClick={() =>
              act(async () => {
                await deleteRule(current.id);
                setPicked("");
                await refresh();
              }, `Deleted “${current.name}”.`)
            }
          >
            Delete
          </Button>
        </div>
      )}

      {note && (
        <p className={`text-2xs ${note.tone}`} role="status">
          {note.text}
        </p>
      )}
      {rules.length >= max && !note && (
        <p className="text-2xs text-faint">You have {max} saved rules, the most there is room for. Delete one to save another.</p>
      )}
    </div>
  );
}
