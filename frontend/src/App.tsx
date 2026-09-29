import { FormEvent, useEffect, useRef, useState } from "react";
import { Account, AccountContext, AnalysisOutput, AnalyzeResponse, Source, User, api, clearSession, getUser, setSession } from "./api";
import { DEMO_EMAIL, SCENARIOS } from "./scenarios";

const ASK_SUGGESTIONS = [
  "What is Priya telling in this mail?",
  "What did we promise Priya?",
  "Who are the stakeholders?",
  "What is this account's ARR?",
  "Should we offer credits?",
  "What happened with SSO?",
  "What prior incidents does this account have?",
];

export default function App() {
  const [user, setUser] = useState<User | null>(getUser());
  if (!user) return <Login onLogin={(token, next) => { setSession(token, next); setUser(next); }} />;
  return (
    <Copilot
      user={user}
      onLogout={() => {
        clearSession();
        setUser(null);
      }}
    />
  );
}

function Login({ onLogin }: { onLogin: (token: string, user: User) => void }) {
  const [email, setEmail] = useState("csm@accrue.demo");
  const [password, setPassword] = useState("AccrueDemo!2026");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const data = await api.login(email, password);
      onLogin(data.access_token, data.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-shell">
      <form className="login-card" onSubmit={submit}>
        <p className="eyebrow">Customer success copilot</p>
        <h1>Accrue</h1>
        <p className="lede">
          When a VIP account escalates, retrieve the history, the landmines, and the plays that actually saved — or lost — similar customers.
        </p>
        <label>Email</label>
        <input value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" />
        <label>Password</label>
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
        {error ? <div className="error">{error}</div> : null}
        <button className="btn btn-primary block" disabled={busy}>
          {busy ? "Signing in…" : "Open workspace"}
        </button>
        <p className="hint">Demo CSM: csm@accrue.demo / AccrueDemo!2026 · Admin: admin@accrue.demo / AccrueAdmin!2026. All customer records are synthetic.</p>
      </form>
    </div>
  );
}

function Copilot({ user, onLogout }: { user: User; onLogout: () => void }) {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountId, setAccountId] = useState("acc_acme");
  const [severity, setSeverity] = useState("P1");
  const [facts, setFacts] = useState("Checkout API 5xx for 26 minutes. No SEV owner confirmed yet.");
  const [text, setText] = useState(DEMO_EMAIL);
  const [memoryMode, setMemoryMode] = useState<"full" | "limited">("full");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [draft, setDraft] = useState("");
  const [correction, setCorrection] = useState("Never offer credits to Priya; escalate to engineering first.");
  const [correctionNote, setCorrectionNote] = useState("");
  const [source, setSource] = useState<Source | null>(null);
  const [copied, setCopied] = useState("");
  const [dossier, setDossier] = useState<AccountContext | null>(null);

  const [askInput, setAskInput] = useState("");
  const [askBusy, setAskBusy] = useState(false);
  const [askError, setAskError] = useState("");
  const [askThread, setAskThread] = useState<{ role: "user" | "accrue"; text: string; citations?: string[] }[]>([]);
  const askThreadRef = useRef<HTMLDivElement>(null);
  const askEndRef = useRef<HTMLDivElement>(null);
  const askInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.accounts().then((data) => setAccounts(data.accounts)).catch((err) => setError(String(err.message)));
  }, []);

  useEffect(() => {
    if (!accountId) return;
    api.context(accountId).then(setDossier).catch(() => setDossier(null));
    setAskThread([]);
    setAskInput("");
    setAskError("");
  }, [accountId]);

  useEffect(() => {
    if (askThread.length === 0 && !askBusy) return;
    const frame = requestAnimationFrame(() => {
      const thread = askThreadRef.current;
      if (thread) thread.scrollTop = thread.scrollHeight;
      askEndRef.current?.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "auto" });
      askInputRef.current?.focus();
    });
    return () => cancelAnimationFrame(frame);
  }, [askThread, askBusy]);

  const account = accounts.find((item) => item.id === accountId);

  async function runAnalyze(payload?: {
    account_id: string;
    escalation_text: string;
    severity: string;
    incident_facts: string;
    memory_mode: "full" | "limited";
  }) {
    const body = payload || {
      account_id: accountId,
      escalation_text: text,
      severity,
      incident_facts: facts,
      memory_mode: memoryMode,
    };
    setBusy(true);
    setError("");
    setCorrectionNote("");
    try {
      const data = await api.analyze(body);
      setResult(data);
      setDraft(data.output.reply_draft);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analyze failed");
    } finally {
      setBusy(false);
    }
  }

  async function askCompany(question?: string) {
    const query = (question ?? askInput).trim();
    if (query.length < 3) {
      setAskError("Type a question about this company.");
      return;
    }
    setAskBusy(true);
    setAskError("");
    setAskInput("");
    setAskThread((current) => [...current, { role: "user", text: query }]);
    try {
      const data = await api.ask(accountId, query, text);
      setAskThread((current) => [
        ...current,
        { role: "accrue", text: data.answer, citations: data.citations },
      ]);
    } catch (err) {
      setAskError(err instanceof Error ? err.message : "Ask failed");
    } finally {
      setAskBusy(false);
    }
  }

  function loadSixtySecondDemo() {
    const demoFacts = "Checkout API 5xx for 26 minutes. No SEV owner confirmed yet.";
    setAccountId("acc_acme");
    setSeverity("P1");
    setFacts(demoFacts);
    setText(DEMO_EMAIL);
    setMemoryMode("full");
    setResult(null);
    setDraft("");
    void runAnalyze({
      account_id: "acc_acme",
      escalation_text: DEMO_EMAIL,
      severity: "P1",
      incident_facts: demoFacts,
      memory_mode: "full",
    });
  }

  async function openSource(id: string) {
    if (id === "current_mail") {
      setSource({
        id: "current_mail",
        type: "current_mail",
        title: "Current escalation mail",
        body: text.trim() || "No mail is pasted in the left panel.",
        source_ref: "live-paste",
      });
      return;
    }
    try {
      const data = await api.source(id);
      setSource(data);
    } catch {
      try {
        const mem = await api.memory(id);
        setSource({
          id,
          type: String(mem.memory.memory_type || "memory"),
          title: id,
          body: String(mem.memory.text || ""),
          source_ref: String(mem.memory.source_ref || ""),
          occurred_at: mem.memory.created_at as string | undefined,
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : "Source unavailable");
      }
    }
  }

  async function saveCorrection() {
    if (!result) return;
    setBusy(true);
    try {
      const preview = await api.previewCorrection(result.escalation_id, {
        proposed_memory: correction,
        memory_type: "team_correction",
        scope: "account",
      });
      const confirmed = await api.confirmCorrection(
        result.escalation_id,
        { correction_id: preview.correction_id, confirm: true },
        crypto.randomUUID()
      );
      setCorrectionNote(`Saved as ${confirmed.memory_id}. Replay Analyze to see it retrieved.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Correction failed");
    } finally {
      setBusy(false);
    }
  }

  async function copyAll() {
    if (!result) return;
    const exported = await api.exportText(result.escalation_id);
    await navigator.clipboard.writeText(exported.text);
    setCopied("Brief copied.");
    setTimeout(() => setCopied(""), 2000);
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <strong>Accrue</strong>
          <span>Live account rescue · synthetic demo corpus</span>
        </div>
        <div className="top-actions">
          <span className="pill">{user.name} · {user.role}</span>
          {user.role === "admin" ? (
            <button className="btn btn-ghost" onClick={() => api.resetDemo().then(() => window.location.reload())}>
              Reset demo data
            </button>
          ) : null}
          <button className="btn btn-ghost" onClick={onLogout}>Sign out</button>
        </div>
      </header>

      <main className="layout">
        <section className="panel">
          <div className="account-head">
            <div>
              <p className="kicker">Account</p>
              <h2 style={{ margin: 0 }}>{account?.name || "Select account"}</h2>
            </div>
            {account ? <div className="arr">${account.arr.toLocaleString()} ARR · {account.status}</div> : null}
          </div>
          <select value={accountId} onChange={(e) => setAccountId(e.target.value)} style={{ margin: "12px 0" }}>
            {accounts.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name} ({item.status})
              </option>
            ))}
          </select>
          <p className="meta">
            Priya’s email is only the live trigger. The full client book below is from Accrue memory (synthetic), not invented from that message.
          </p>
          {dossier ? (
            <div className="dossier">
              <p className="kicker">Client book · memory, not this email</p>
              <p className="meta">
                {dossier.account.name} · ${dossier.account.arr.toLocaleString()} ARR · {dossier.account.segment} · {dossier.account.timezone} · {dossier.account.status}
              </p>
              <p className="kicker">People</p>
              {dossier.stakeholders.map((person) => (
                <div className="fact" key={person.id}>
                  <strong>{person.name}</strong> · {person.role}
                  <div className="meta">{person.preferences}</div>
                </div>
              ))}
              <p className="kicker">Commitments</p>
              {dossier.commitments.map((item) => (
                <div className="fact" key={item.id}>
                  <span className="ids">{item.status}</span> {item.description}
                </div>
              ))}
              <p className="kicker">Prior incidents</p>
              {dossier.incidents.map((item) => (
                <div className="fact" key={item.id}>
                  {item.severity}: {item.summary}
                </div>
              ))}
            </div>
          ) : null}

          <p className="kicker" style={{ marginTop: 16 }}>Scripted scenarios</p>
          <div className="chips">
            {SCENARIOS.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`chip${accountId === item.accountId && text === item.text ? " active" : ""}`}
                disabled={busy}
                onClick={() => {
                  const mode = item.memoryMode || "full";
                  setAccountId(item.accountId);
                  setText(item.text);
                  setMemoryMode(mode);
                  setSeverity("P1");
                  void runAnalyze({
                    account_id: item.accountId,
                    escalation_text: item.text,
                    severity: "P1",
                    incident_facts: facts,
                    memory_mode: mode,
                  });
                }}
              >
                {item.label}
              </button>
            ))}
          </div>

          <div className="row">
            <div>
              <label>Severity</label>
              <select value={severity} onChange={(e) => setSeverity(e.target.value)}>
                <option>P1</option>
                <option>P2</option>
                <option>P3</option>
              </select>
            </div>
            <div>
              <label>Memory</label>
              <select value={memoryMode} onChange={(e) => setMemoryMode(e.target.value as "full" | "limited")}>
                <option value="full">Full (Hindsight on)</option>
                <option value="limited">Limited (memory off)</option>
              </select>
            </div>
          </div>
          <label>Incident facts (optional)</label>
          <input value={facts} onChange={(e) => setFacts(e.target.value)} />
          <label>Escalation email or note</label>
          <textarea value={text} onChange={(e) => setText(e.target.value)} />
          {error ? <div className="error">{error}</div> : null}
          <div className="actions">
            <button className="btn btn-primary" type="button" disabled={busy} onClick={loadSixtySecondDemo}>
              {busy ? "Running 60s demo…" : "Run 60s demo"}
            </button>
            <button className="btn btn-ghost" type="button" disabled={busy} onClick={() => void runAnalyze()}>
              Analyze current note
            </button>
          </div>
        </section>

        <aside className="panel ask-window">
          <p className="kicker">Ask this company</p>
          <h2 style={{ margin: "0 0 6px" }}>{account?.name || "Select an account"}</h2>
          <p className="meta">Questions are answered only from this account’s approved memory. Accrue will not invent facts.</p>
          <div className="chips">
            {ASK_SUGGESTIONS.map((item) => (
              <button key={item} type="button" className="chip" disabled={askBusy} onClick={() => void askCompany(item)}>
                {item}
              </button>
            ))}
          </div>
          <div className="ask-thread" ref={askThreadRef}>
            {askThread.length === 0 ? (
              <p className="meta">Try “What did we promise Priya?” or “Should we offer credits?”</p>
            ) : (
              askThread.map((message, index) => (
                <div key={`${message.role}-${index}`} className={`ask-bubble ${message.role}`}>
                  <strong>{message.role === "user" ? "You" : "Accrue"}</strong>
                  <pre>{message.text}</pre>
                  {message.citations?.length ? (
                    <div>
                      {message.citations.map((id) => (
                        <button key={id} type="button" className="source-btn" onClick={() => void openSource(id)}>
                          {id}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              ))
            )}
            <div ref={askEndRef} className="ask-end" aria-hidden="true" />
          </div>
          {askError ? <div className="error">{askError}</div> : null}
          <form
            className="ask-form"
            onSubmit={(event) => {
              event.preventDefault();
              void askCompany();
            }}
          >
            <input
              ref={askInputRef}
              value={askInput}
              onChange={(e) => setAskInput(e.target.value)}
              placeholder={`Ask about ${account?.name || "this account"}…`}
              readOnly={askBusy}
            />
            <button className="btn btn-primary" type="submit" disabled={askBusy}>
              {askBusy ? "Asking…" : "Ask"}
            </button>
          </form>
        </aside>

        <section className="results">
          {!result ? (
            <div className="panel empty">
              <div>
                <h2>Run the 60-second demo</h2>
                <p>Click <strong>Run 60s demo</strong> to load Priya’s Acme escalation and generate the grounded brief.</p>
              </div>
            </div>
          ) : (
            <>
              <OutputPanel output={result.output} latency={result.latency_ms} onOpen={openSource} />
              <div className="panel">
                <p className="kicker">Editable reply · Accrue does not send</p>
                <textarea className="draft" value={draft} onChange={(e) => setDraft(e.target.value)} />
                <div className="actions">
                  <button className="btn btn-primary" onClick={() => navigator.clipboard.writeText(draft).then(() => setCopied("Draft copied."))}>
                    Copy draft
                  </button>
                  <button className="btn btn-ghost" onClick={copyAll}>Export brief</button>
                  {copied ? <span className="pill">{copied}</span> : null}
                </div>
              </div>
              <div className="panel">
                <p className="kicker">Correct memory</p>
                <p className="meta">Preview, then confirm. This writes a scoped, authored memory — it does not overwrite historical source records.</p>
                <textarea value={correction} onChange={(e) => setCorrection(e.target.value)} style={{ minHeight: 90 }} />
                <div className="actions">
                  <button className="btn btn-danger" disabled={busy} onClick={saveCorrection}>
                    Preview & save correction
                  </button>
                </div>
                {correctionNote ? <div className="banner ok" style={{ marginTop: 12 }}>{correctionNote}</div> : null}
              </div>
            </>
          )}
        </section>
      </main>
      {source ? (
        <div className="modal-back" onClick={() => setSource(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <p className="kicker">{source.type}</p>
            <h3>{source.title}</h3>
            <p className="ids">{source.id} · {source.source_ref}</p>
            <pre>{source.body}</pre>
            <button className="btn btn-ghost" onClick={() => setSource(null)}>Close</button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function OutputPanel({
  output,
  latency,
  onOpen,
}: {
  output: AnalysisOutput;
  latency: number;
  onOpen: (id: string) => void;
}) {
  return (
    <>
      {output.memory_limited ? (
        <div className="banner">Memory-limited: historical claims omitted. Do not treat this as account truth.</div>
      ) : null}
      <div className="panel">
        <div className="account-head">
          <p className="kicker">20-second brief</p>
          <span className="arr">{latency} ms · human review required</span>
        </div>
        <ul className="brief">
          {output.brief.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <p className="meta">{output.confidence_notes}</p>
      </div>
      <div className="grid-2">
        <div className="panel">
          <p className="kicker">Known facts</p>
          {output.known_facts.map((fact) => (
            <div className="fact" key={fact.text}>
              <div>{fact.text}</div>
              <div>
                {fact.source_ids.map((id) => (
                  <button key={id} className="source-btn" onClick={() => onOpen(id)}>
                    {id}
                  </button>
                ))}
                <span className="ids">{fact.verification_status}</span>
              </div>
            </div>
          ))}
          <p className="kicker">Unknowns</p>
          <ul>
            {output.unknowns.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
        <div className="panel">
          <p className="kicker">Do</p>
          {output.do.map((item) => (
            <div className="reco do" key={item.action}>
              <strong>{item.action}</strong>
              <div className="meta">{item.rationale}</div>
              <div>
                {item.evidence_ids.map((id) => (
                  <button key={id} className="source-btn" onClick={() => onOpen(id)}>
                    {id}
                  </button>
                ))}
              </div>
            </div>
          ))}
          <p className="kicker">Don’t</p>
          {output.dont.map((item) => (
            <div className="reco dont" key={item.action}>
              <strong>{item.action}</strong>
              <div className="meta">{item.rationale}</div>
              <div>
                {item.evidence_ids.map((id) => (
                  <button key={id} className="source-btn" onClick={() => onOpen(id)}>
                    {id}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
