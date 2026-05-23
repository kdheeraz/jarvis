import { useEffect, useMemo, useState } from 'react';
import {
  Save,
  RefreshCw,
  RotateCcw,
  Settings as SettingsIcon,
  Brain,
  Mic,
  Database,
  Wrench,
  Shield,
  HardDrive,
  Code2,
  Check,
  AlertCircle,
} from 'lucide-react';
import clsx from 'clsx';
import { getConfig, updateConfig, reloadConfig } from '../../api/admin';

type AnyRecord = Record<string, any>;

const SECTIONS = [
  { id: 'general', label: 'General', icon: SettingsIcon },
  { id: 'llm', label: 'LLM', icon: Brain },
  { id: 'voice', label: 'Voice', icon: Mic },
  { id: 'rag', label: 'RAG', icon: Database },
  { id: 'tools', label: 'Tools', icon: Wrench },
  { id: 'auth', label: 'Auth', icon: Shield },
  { id: 'database', label: 'Database', icon: HardDrive },
  { id: 'advanced', label: 'Advanced (JSON)', icon: Code2 },
] as const;
type SectionId = (typeof SECTIONS)[number]['id'];

const LLM_PROVIDERS = ['ollama', 'openai', 'anthropic', 'bedrock', 'groq'] as const;
const STT_MODELS = ['distil-whisper', 'faster-whisper'] as const;
const TTS_MODELS = ['piper', 'kokoro', 'chattts', 'edge', 'groq'] as const;
const RAG_STORES = ['faiss', 'chromadb', 'opensearch', 'pgvector'] as const;
const ALL_TOOLS = ['web_search', 'datetime_tool', 'calculator', 'rag_search'] as const;

function getPath(obj: AnyRecord, path: string): any {
  return path.split('.').reduce<any>((o, k) => (o == null ? o : o[k]), obj);
}

function setPath(obj: AnyRecord, path: string, value: any): AnyRecord {
  const keys = path.split('.');
  const next = { ...obj };
  let cursor: AnyRecord = next;
  for (let i = 0; i < keys.length - 1; i++) {
    const k = keys[i];
    cursor[k] = { ...(cursor[k] ?? {}) };
    cursor = cursor[k];
  }
  cursor[keys[keys.length - 1]] = value;
  return next;
}

function buildPatch(original: AnyRecord, draft: AnyRecord): AnyRecord {
  const patch: AnyRecord = {};
  for (const key of Object.keys(draft)) {
    const a = draft[key];
    const b = original?.[key];
    if (a && typeof a === 'object' && !Array.isArray(a)) {
      const sub = buildPatch(b ?? {}, a);
      if (Object.keys(sub).length > 0) patch[key] = sub;
    } else if (JSON.stringify(a) !== JSON.stringify(b)) {
      patch[key] = a;
    }
  }
  return patch;
}

function stripRedacted(patch: AnyRecord): AnyRecord {
  if (!patch || typeof patch !== 'object') return patch;
  if (Array.isArray(patch)) return patch;
  const out: AnyRecord = {};
  for (const [k, v] of Object.entries(patch)) {
    if (v === '***') continue;
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      const sub = stripRedacted(v);
      if (Object.keys(sub).length > 0) out[k] = sub;
    } else {
      out[k] = v;
    }
  }
  return out;
}

function countChanges(patch: AnyRecord): number {
  let n = 0;
  const walk = (o: any) => {
    if (o && typeof o === 'object' && !Array.isArray(o)) {
      for (const v of Object.values(o)) walk(v);
    } else {
      n += 1;
    }
  };
  walk(patch);
  return n;
}

export function ConfigPage() {
  const [original, setOriginal] = useState<AnyRecord | null>(null);
  const [draft, setDraft] = useState<AnyRecord | null>(null);
  const [section, setSection] = useState<SectionId>('general');
  const [saving, setSaving] = useState(false);
  const [reloading, setReloading] = useState(false);
  const [message, setMessage] = useState<{ kind: 'ok' | 'err'; text: string } | null>(null);
  const [advancedText, setAdvancedText] = useState('');

  useEffect(() => {
    getConfig().then((c) => {
      setOriginal(c);
      setDraft(c);
    }).catch(() => {});
  }, []);

  const patch = useMemo(() => {
    if (!original || !draft) return {};
    return stripRedacted(buildPatch(original, draft));
  }, [original, draft]);

  const changeCount = countChanges(patch);
  const dirty = changeCount > 0;

  const set = (path: string, value: any) => {
    if (!draft) return;
    setDraft(setPath(draft, path, value));
  };

  const handleSave = async () => {
    if (!dirty) return;
    setSaving(true);
    setMessage(null);
    try {
      await updateConfig(patch);
      const fresh = await getConfig();
      setOriginal(fresh);
      setDraft(fresh);
      setMessage({ kind: 'ok', text: 'Configuration saved and reloaded.' });
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || 'Failed to save';
      setMessage({ kind: 'err', text: typeof detail === 'string' ? detail : JSON.stringify(detail) });
    }
    setSaving(false);
  };

  const handleReset = () => {
    setDraft(original);
    setMessage(null);
  };

  const handleReload = async () => {
    setReloading(true);
    setMessage(null);
    try {
      await reloadConfig();
      const fresh = await getConfig();
      setOriginal(fresh);
      setDraft(fresh);
      setMessage({ kind: 'ok', text: 'Configuration reloaded from disk.' });
    } catch {
      setMessage({ kind: 'err', text: 'Failed to reload configuration.' });
    }
    setReloading(false);
  };

  const handleAdvancedApply = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const updates = JSON.parse(advancedText);
      await updateConfig(updates);
      const fresh = await getConfig();
      setOriginal(fresh);
      setDraft(fresh);
      setAdvancedText('');
      setMessage({ kind: 'ok', text: 'Advanced patch applied.' });
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || 'Invalid JSON';
      setMessage({ kind: 'err', text: typeof detail === 'string' ? detail : JSON.stringify(detail) });
    }
    setSaving(false);
  };

  if (!draft) {
    return <div className="text-surface-500">Loading configuration…</div>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Configuration</h1>
          <p className="text-sm text-surface-500 mt-1">
            Edit settings inline. Changes are saved to <code className="text-xs">config/config.yaml</code> and reloaded live.
          </p>
        </div>
        <button
          onClick={handleReload}
          disabled={reloading}
          className="btn-secondary flex items-center gap-2"
        >
          <RefreshCw size={16} className={reloading ? 'animate-spin' : ''} />
          Reload from disk
        </button>
      </div>

      {message && (
        <div
          className={clsx(
            'mb-4 px-4 py-3 rounded-xl text-sm flex items-start gap-2',
            message.kind === 'ok'
              ? 'bg-green-50 dark:bg-green-950/40 text-green-700 dark:text-green-300'
              : 'bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300',
          )}
        >
          {message.kind === 'ok' ? <Check size={16} className="mt-0.5" /> : <AlertCircle size={16} className="mt-0.5" />}
          <span>{message.text}</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6">
        {/* Sidebar */}
        <nav className="card p-2 self-start sticky top-4">
          {SECTIONS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setSection(id)}
              className={clsx(
                'w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-left transition-colors',
                section === id
                  ? 'bg-primary-600 text-white'
                  : 'hover:bg-white/40 dark:hover:bg-white/5 text-surface-700 dark:text-surface-200',
              )}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </nav>

        {/* Body */}
        <div className="space-y-6">
          {section === 'general' && <GeneralSection draft={draft} set={set} />}
          {section === 'llm' && <LLMSection draft={draft} set={set} />}
          {section === 'voice' && <VoiceSection draft={draft} set={set} />}
          {section === 'rag' && <RAGSection draft={draft} set={set} />}
          {section === 'tools' && <ToolsSection draft={draft} set={set} />}
          {section === 'auth' && <AuthSection draft={draft} set={set} />}
          {section === 'database' && <DatabaseSection draft={draft} set={set} />}
          {section === 'advanced' && (
            <AdvancedSection
              text={advancedText}
              setText={setAdvancedText}
              onApply={handleAdvancedApply}
              saving={saving}
            />
          )}

          {section !== 'advanced' && (
            <div className="card p-4 flex items-center justify-between sticky bottom-4">
              <div className="text-sm text-surface-500">
                {dirty ? (
                  <>
                    <span className="font-medium text-surface-900 dark:text-surface-100">
                      {changeCount} change{changeCount === 1 ? '' : 's'}
                    </span>{' '}
                    pending
                  </>
                ) : (
                  'No pending changes'
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleReset}
                  disabled={!dirty || saving}
                  className="btn-secondary flex items-center gap-2"
                >
                  <RotateCcw size={16} />
                  Discard
                </button>
                <button
                  onClick={handleSave}
                  disabled={!dirty || saving}
                  className="btn-primary flex items-center gap-2"
                >
                  <Save size={16} />
                  {saving ? 'Saving…' : 'Save & apply'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ---------- Generic field primitives ---------- */

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <div className="flex items-baseline justify-between mb-1.5">
        <span className="text-sm font-medium">{label}</span>
        {hint && <span className="text-xs text-surface-500">{hint}</span>}
      </div>
      {children}
    </label>
  );
}

function TextInput({
  value,
  onChange,
  placeholder,
  type = 'text',
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <input
      type={type}
      value={value ?? ''}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="input-field"
    />
  );
}

function NumberInput({
  value,
  onChange,
  step = 1,
  min,
  max,
}: {
  value: number;
  onChange: (v: number) => void;
  step?: number;
  min?: number;
  max?: number;
}) {
  return (
    <input
      type="number"
      value={Number.isFinite(value) ? value : 0}
      step={step}
      min={min}
      max={max}
      onChange={(e) => onChange(parseFloat(e.target.value))}
      className="input-field"
    />
  );
}

function Select({
  value,
  onChange,
  options,
}: {
  value: string;
  onChange: (v: string) => void;
  options: readonly string[] | { value: string; label: string }[];
}) {
  const opts =
    Array.isArray(options) && options.length > 0 && typeof (options as any)[0] === 'object'
      ? (options as { value: string; label: string }[])
      : (options as readonly string[]).map((o) => ({ value: o, label: o }));
  return (
    <select
      value={value ?? ''}
      onChange={(e) => onChange(e.target.value)}
      className="input-field"
    >
      {opts.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

function Toggle({
  value,
  onChange,
  label,
  description,
}: {
  value: boolean;
  onChange: (v: boolean) => void;
  label: string;
  description?: string;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <div className="text-sm font-medium">{label}</div>
        {description && <div className="text-xs text-surface-500 mt-0.5">{description}</div>}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={value}
        onClick={() => onChange(!value)}
        className={clsx(
          'relative inline-flex h-6 w-11 shrink-0 rounded-full transition-colors',
          value ? 'bg-primary-600' : 'bg-surface-300 dark:bg-surface-700',
        )}
      >
        <span
          className={clsx(
            'inline-block h-5 w-5 transform rounded-full bg-white shadow translate-y-0.5 transition-transform',
            value ? 'translate-x-5' : 'translate-x-0.5',
          )}
        />
      </button>
    </div>
  );
}

function SectionCard({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="card p-6">
      <div className="mb-5">
        <h2 className="text-lg font-semibold">{title}</h2>
        {description && <p className="text-sm text-surface-500 mt-1">{description}</p>}
      </div>
      <div className="space-y-4">{children}</div>
    </div>
  );
}

function Grid2({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">{children}</div>;
}

/* ---------- Sections ---------- */

function GeneralSection({ draft, set }: { draft: AnyRecord; set: (path: string, v: any) => void }) {
  return (
    <SectionCard title="General" description="Application identity and HTTP server settings.">
      <Grid2>
        <Field label="App name">
          <TextInput value={draft.app?.name} onChange={(v) => set('app.name', v)} />
        </Field>
        <Field label="Theme color" hint="hex">
          <div className="flex items-center gap-2">
            <input
              type="color"
              value={draft.app?.theme || '#3b82f6'}
              onChange={(e) => set('app.theme', e.target.value)}
              className="h-10 w-12 rounded-lg border border-white/40 dark:border-white/10 cursor-pointer bg-transparent"
            />
            <TextInput value={draft.app?.theme} onChange={(v) => set('app.theme', v)} />
          </div>
        </Field>
        <Field label="Host">
          <TextInput value={draft.app?.host} onChange={(v) => set('app.host', v)} />
        </Field>
        <Field label="Port">
          <NumberInput value={draft.app?.port} onChange={(v) => set('app.port', v)} min={1} max={65535} />
        </Field>
      </Grid2>
      <Toggle
        value={!!draft.app?.debug}
        onChange={(v) => set('app.debug', v)}
        label="Debug mode"
        description="Verbose logs, hot-reload friendly behavior."
      />
    </SectionCard>
  );
}

function LLMSection({ draft, set }: { draft: AnyRecord; set: (path: string, v: any) => void }) {
  const provider: string = draft.llm?.provider || 'ollama';

  return (
    <>
      <SectionCard title="LLM provider" description="Choose where the agent's model runs.">
        <Field label="Provider">
          <Select
            value={provider}
            onChange={(v) => set('llm.provider', v)}
            options={LLM_PROVIDERS as unknown as readonly string[]}
          />
        </Field>
        <Field label="System prompt" hint="prepended to every conversation">
          <textarea
            value={draft.llm?.system_prompt ?? ''}
            onChange={(e) => set('llm.system_prompt', e.target.value)}
            className="input-field min-h-[90px] font-mono text-sm"
          />
        </Field>
      </SectionCard>

      {provider === 'ollama' && (
        <SectionCard title="Ollama settings">
          <Grid2>
            <Field label="Model">
              <TextInput value={draft.llm?.ollama?.model} onChange={(v) => set('llm.ollama.model', v)} />
            </Field>
            <Field label="Base URL">
              <TextInput value={draft.llm?.ollama?.base_url} onChange={(v) => set('llm.ollama.base_url', v)} />
            </Field>
            <Field label="Temperature">
              <NumberInput
                value={draft.llm?.ollama?.temperature ?? 0.7}
                onChange={(v) => set('llm.ollama.temperature', v)}
                step={0.05}
                min={0}
                max={2}
              />
            </Field>
          </Grid2>
          <Toggle
            value={!!draft.llm?.ollama?.reasoning}
            onChange={(v) => set('llm.ollama.reasoning', v)}
            label="Reasoning"
            description="Enable thinking-mode for reasoning-capable models."
          />
        </SectionCard>
      )}

      {provider === 'openai' && (
        <SectionCard title="OpenAI settings">
          <Grid2>
            <Field label="Model">
              <TextInput value={draft.llm?.openai?.model} onChange={(v) => set('llm.openai.model', v)} />
            </Field>
            <Field label="API key" hint="leave *** to keep current">
              <TextInput
                type="password"
                value={draft.llm?.openai?.api_key ?? ''}
                onChange={(v) => set('llm.openai.api_key', v)}
                placeholder="sk-…"
              />
            </Field>
            <Field label="Temperature">
              <NumberInput
                value={draft.llm?.openai?.temperature ?? 0.7}
                onChange={(v) => set('llm.openai.temperature', v)}
                step={0.05}
                min={0}
                max={2}
              />
            </Field>
          </Grid2>
        </SectionCard>
      )}

      {provider === 'anthropic' && (
        <SectionCard title="Anthropic settings">
          <Grid2>
            <Field label="Model">
              <TextInput value={draft.llm?.anthropic?.model} onChange={(v) => set('llm.anthropic.model', v)} />
            </Field>
            <Field label="API key" hint="leave *** to keep current">
              <TextInput
                type="password"
                value={draft.llm?.anthropic?.api_key ?? ''}
                onChange={(v) => set('llm.anthropic.api_key', v)}
                placeholder="sk-ant-…"
              />
            </Field>
            <Field label="Temperature">
              <NumberInput
                value={draft.llm?.anthropic?.temperature ?? 0.7}
                onChange={(v) => set('llm.anthropic.temperature', v)}
                step={0.05}
                min={0}
                max={2}
              />
            </Field>
          </Grid2>
        </SectionCard>
      )}

      {provider === 'bedrock' && (
        <SectionCard title="AWS Bedrock settings" description="Credentials are read from the AWS_* environment variables.">
          <Grid2>
            <Field label="Model ID">
              <TextInput
                value={draft.llm?.bedrock?.model_id}
                onChange={(v) => set('llm.bedrock.model_id', v)}
              />
            </Field>
            <Field label="Region">
              <TextInput value={draft.llm?.bedrock?.region} onChange={(v) => set('llm.bedrock.region', v)} />
            </Field>
            <Field label="Temperature">
              <NumberInput
                value={draft.llm?.bedrock?.temperature ?? 0.7}
                onChange={(v) => set('llm.bedrock.temperature', v)}
                step={0.05}
                min={0}
                max={2}
              />
            </Field>
          </Grid2>
        </SectionCard>
      )}

      {provider === 'groq' && (
        <SectionCard title="Groq settings">
          <Grid2>
            <Field label="Model">
              <TextInput value={draft.llm?.groq?.model} onChange={(v) => set('llm.groq.model', v)} />
            </Field>
            <Field label="API key" hint="or set GROQ_API_KEY env">
              <TextInput
                type="password"
                value={draft.llm?.groq?.api_key ?? ''}
                onChange={(v) => set('llm.groq.api_key', v)}
                placeholder="gsk-…"
              />
            </Field>
            <Field label="Temperature">
              <NumberInput
                value={draft.llm?.groq?.temperature ?? 0.7}
                onChange={(v) => set('llm.groq.temperature', v)}
                step={0.05}
                min={0}
                max={2}
              />
            </Field>
          </Grid2>
        </SectionCard>
      )}
    </>
  );
}

function VoiceSection({ draft, set }: { draft: AnyRecord; set: (path: string, v: any) => void }) {
  const stt = draft.voice?.stt_model;
  const tts = draft.voice?.tts_model;

  return (
    <>
      <SectionCard title="Voice mode">
        <Toggle
          value={!!draft.voice?.enabled}
          onChange={(v) => set('voice.enabled', v)}
          label="Enable voice mode"
          description="Adds the WebRTC voice button to the chat UI."
        />
        <Grid2>
          <Field label="Speech-to-text">
            <Select value={stt} onChange={(v) => set('voice.stt_model', v)} options={STT_MODELS as unknown as readonly string[]} />
          </Field>
          <Field label="Text-to-speech">
            <Select value={tts} onChange={(v) => set('voice.tts_model', v)} options={TTS_MODELS as unknown as readonly string[]} />
          </Field>
        </Grid2>
      </SectionCard>

      {stt === 'faster-whisper' && (
        <SectionCard title="faster-whisper settings">
          <Grid2>
            <Field label="Model size">
              <TextInput
                value={draft.voice?.faster_whisper?.model_size}
                onChange={(v) => set('voice.faster_whisper.model_size', v)}
              />
            </Field>
            <Field label="Device">
              <Select
                value={draft.voice?.faster_whisper?.device || 'cpu'}
                onChange={(v) => set('voice.faster_whisper.device', v)}
                options={['cpu', 'cuda', 'mps']}
              />
            </Field>
            <Field label="Compute type">
              <TextInput
                value={draft.voice?.faster_whisper?.compute_type}
                onChange={(v) => set('voice.faster_whisper.compute_type', v)}
              />
            </Field>
            <Field label="Beam size">
              <NumberInput
                value={draft.voice?.faster_whisper?.beam_size ?? 1}
                onChange={(v) => set('voice.faster_whisper.beam_size', v)}
                min={1}
                max={10}
              />
            </Field>
            <Field label="Language">
              <TextInput
                value={draft.voice?.faster_whisper?.language ?? ''}
                onChange={(v) => set('voice.faster_whisper.language', v)}
              />
            </Field>
          </Grid2>
          <Toggle
            value={!!draft.voice?.faster_whisper?.vad_filter}
            onChange={(v) => set('voice.faster_whisper.vad_filter', v)}
            label="VAD filter"
          />
        </SectionCard>
      )}

      {tts === 'piper' && (
        <SectionCard title="Piper TTS">
          <Grid2>
            <Field label="Model path">
              <TextInput
                value={draft.voice?.piper?.model_path}
                onChange={(v) => set('voice.piper.model_path', v)}
              />
            </Field>
            <Field label="Config path">
              <TextInput
                value={draft.voice?.piper?.config_path}
                onChange={(v) => set('voice.piper.config_path', v)}
              />
            </Field>
          </Grid2>
        </SectionCard>
      )}

      {tts === 'edge' && (
        <SectionCard title="Edge TTS">
          <Grid2>
            <Field label="Voice">
              <TextInput value={draft.voice?.edge?.voice} onChange={(v) => set('voice.edge.voice', v)} />
            </Field>
            <Field label="Rate">
              <TextInput value={draft.voice?.edge?.rate} onChange={(v) => set('voice.edge.rate', v)} />
            </Field>
            <Field label="Pitch">
              <TextInput value={draft.voice?.edge?.pitch} onChange={(v) => set('voice.edge.pitch', v)} />
            </Field>
          </Grid2>
        </SectionCard>
      )}

      {tts === 'kokoro' && (
        <SectionCard title="Kokoro TTS">
          <Grid2>
            <Field label="Voice">
              <TextInput value={draft.voice?.kokoro?.voice} onChange={(v) => set('voice.kokoro.voice', v)} />
            </Field>
            <Field label="Speed">
              <NumberInput
                value={draft.voice?.kokoro?.speed ?? 1}
                onChange={(v) => set('voice.kokoro.speed', v)}
                step={0.05}
                min={0.5}
                max={2}
              />
            </Field>
            <Field label="Language">
              <TextInput value={draft.voice?.kokoro?.lang} onChange={(v) => set('voice.kokoro.lang', v)} />
            </Field>
          </Grid2>
        </SectionCard>
      )}

      {tts === 'groq' && (
        <SectionCard title="Groq TTS">
          <Grid2>
            <Field label="Voice">
              <TextInput value={draft.voice?.groq?.voice} onChange={(v) => set('voice.groq.voice', v)} />
            </Field>
            <Field label="Model">
              <TextInput value={draft.voice?.groq?.model} onChange={(v) => set('voice.groq.model', v)} />
            </Field>
            <Field label="Base URL">
              <TextInput value={draft.voice?.groq?.base_url} onChange={(v) => set('voice.groq.base_url', v)} />
            </Field>
            <Field label="API key env var">
              <TextInput
                value={draft.voice?.groq?.api_key_env}
                onChange={(v) => set('voice.groq.api_key_env', v)}
              />
            </Field>
          </Grid2>
        </SectionCard>
      )}

      {tts === 'chattts' && (
        <SectionCard title="ChatTTS">
          <Grid2>
            <Field label="Device">
              <Select
                value={draft.voice?.chattts?.device || 'cpu'}
                onChange={(v) => set('voice.chattts.device', v)}
                options={['cpu', 'cuda', 'mps']}
              />
            </Field>
            <Field label="Speaker seed">
              <NumberInput
                value={draft.voice?.chattts?.speaker_seed ?? 42}
                onChange={(v) => set('voice.chattts.speaker_seed', v)}
              />
            </Field>
            <Field label="Temperature">
              <NumberInput
                value={draft.voice?.chattts?.temperature ?? 0.3}
                onChange={(v) => set('voice.chattts.temperature', v)}
                step={0.05}
                min={0}
                max={2}
              />
            </Field>
            <Field label="Top-p">
              <NumberInput
                value={draft.voice?.chattts?.top_p ?? 0.7}
                onChange={(v) => set('voice.chattts.top_p', v)}
                step={0.05}
                min={0}
                max={1}
              />
            </Field>
            <Field label="Top-k">
              <NumberInput
                value={draft.voice?.chattts?.top_k ?? 20}
                onChange={(v) => set('voice.chattts.top_k', v)}
                min={1}
              />
            </Field>
            <Field label="Sample rate">
              <NumberInput
                value={draft.voice?.chattts?.sample_rate ?? 24000}
                onChange={(v) => set('voice.chattts.sample_rate', v)}
              />
            </Field>
          </Grid2>
          <Toggle
            value={!!draft.voice?.chattts?.compile}
            onChange={(v) => set('voice.chattts.compile', v)}
            label="torch.compile warmup"
            description="GPU-only first-run warmup."
          />
        </SectionCard>
      )}

      <SectionCard title="Emotion tags" description="Inline cues like <laugh>, <sigh> for expressive backends.">
        <Toggle
          value={!!draft.voice?.emotion_tags?.enabled}
          onChange={(v) => set('voice.emotion_tags.enabled', v)}
          label="Enabled"
          description="Disable for Piper / Edge / Kokoro — they would speak the tags literally."
        />
      </SectionCard>
    </>
  );
}

function RAGSection({ draft, set }: { draft: AnyRecord; set: (path: string, v: any) => void }) {
  const store: string = draft.rag?.store || 'faiss';
  return (
    <>
      <SectionCard title="Retrieval-Augmented Generation">
        <Toggle
          value={!!draft.rag?.enabled}
          onChange={(v) => set('rag.enabled', v)}
          label="Enable RAG"
          description="Adds the rag_search tool and document ingestion."
        />
        <Grid2>
          <Field label="Vector store">
            <Select
              value={store}
              onChange={(v) => set('rag.store', v)}
              options={RAG_STORES as unknown as readonly string[]}
            />
          </Field>
          <Field label="Embedding model">
            <TextInput
              value={draft.rag?.embedding_model}
              onChange={(v) => set('rag.embedding_model', v)}
            />
          </Field>
          <Field label="Chunk size">
            <NumberInput
              value={draft.rag?.chunk_size ?? 1000}
              onChange={(v) => set('rag.chunk_size', v)}
              min={100}
            />
          </Field>
          <Field label="Chunk overlap">
            <NumberInput
              value={draft.rag?.chunk_overlap ?? 200}
              onChange={(v) => set('rag.chunk_overlap', v)}
              min={0}
            />
          </Field>
        </Grid2>
      </SectionCard>

      {store === 'faiss' && (
        <SectionCard title="FAISS">
          <Field label="Index path">
            <TextInput
              value={draft.rag?.faiss?.index_path}
              onChange={(v) => set('rag.faiss.index_path', v)}
            />
          </Field>
        </SectionCard>
      )}
      {store === 'chromadb' && (
        <SectionCard title="ChromaDB">
          <Grid2>
            <Field label="Host">
              <TextInput
                value={draft.rag?.chromadb?.host}
                onChange={(v) => set('rag.chromadb.host', v)}
              />
            </Field>
            <Field label="Port">
              <NumberInput
                value={draft.rag?.chromadb?.port ?? 8000}
                onChange={(v) => set('rag.chromadb.port', v)}
              />
            </Field>
          </Grid2>
        </SectionCard>
      )}
      {store === 'opensearch' && (
        <SectionCard title="OpenSearch">
          <Grid2>
            <Field label="Host">
              <TextInput
                value={draft.rag?.opensearch?.host}
                onChange={(v) => set('rag.opensearch.host', v)}
              />
            </Field>
            <Field label="Port">
              <NumberInput
                value={draft.rag?.opensearch?.port ?? 9200}
                onChange={(v) => set('rag.opensearch.port', v)}
              />
            </Field>
          </Grid2>
        </SectionCard>
      )}
      {store === 'pgvector' && (
        <SectionCard title="pgvector">
          <Field label="Connection string">
            <TextInput
              value={draft.rag?.pgvector?.connection_string}
              onChange={(v) => set('rag.pgvector.connection_string', v)}
            />
          </Field>
        </SectionCard>
      )}
    </>
  );
}

function ToolsSection({ draft, set }: { draft: AnyRecord; set: (path: string, v: any) => void }) {
  const enabled: string[] = draft.tools?.enabled || [];
  const toggle = (name: string) => {
    const next = enabled.includes(name) ? enabled.filter((n) => n !== name) : [...enabled, name];
    set('tools.enabled', next);
  };
  return (
    <SectionCard title="Built-in tools" description="Tools the agent can call. The rag_search tool requires RAG to be enabled.">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {ALL_TOOLS.map((name) => {
          const on = enabled.includes(name);
          return (
            <button
              key={name}
              type="button"
              onClick={() => toggle(name)}
              className={clsx(
                'text-left px-4 py-3 rounded-xl border transition-colors',
                on
                  ? 'bg-primary-600/10 border-primary-500/60'
                  : 'bg-white/30 dark:bg-white/5 border-white/40 dark:border-white/10 hover:bg-white/50 dark:hover:bg-white/10',
              )}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-sm">{name}</span>
                <span
                  className={clsx(
                    'text-xs px-2 py-0.5 rounded-full',
                    on
                      ? 'bg-primary-600 text-white'
                      : 'bg-surface-200 dark:bg-surface-700 text-surface-600 dark:text-surface-300',
                  )}
                >
                  {on ? 'Enabled' : 'Disabled'}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </SectionCard>
  );
}

function AuthSection({ draft, set }: { draft: AnyRecord; set: (path: string, v: any) => void }) {
  return (
    <SectionCard title="Authentication" description="Admin login and JWT settings.">
      <Toggle
        value={!!draft.auth?.enabled}
        onChange={(v) => set('auth.enabled', v)}
        label="Require admin login"
      />
      <Grid2>
        <Field label="Admin username">
          <TextInput
            value={draft.auth?.admin_username}
            onChange={(v) => set('auth.admin_username', v)}
          />
        </Field>
        <Field label="Admin password" hint="leave *** to keep current">
          <TextInput
            type="password"
            value={draft.auth?.admin_password ?? ''}
            onChange={(v) => set('auth.admin_password', v)}
          />
        </Field>
        <Field label="JWT expiry (minutes)">
          <NumberInput
            value={draft.auth?.jwt_expiry_minutes ?? 1440}
            onChange={(v) => set('auth.jwt_expiry_minutes', v)}
            min={1}
          />
        </Field>
        <Field label="JWT secret" hint="leave *** to keep current">
          <TextInput
            type="password"
            value={draft.auth?.jwt_secret_key ?? ''}
            onChange={(v) => set('auth.jwt_secret_key', v)}
          />
        </Field>
      </Grid2>
    </SectionCard>
  );
}

function DatabaseSection({ draft, set }: { draft: AnyRecord; set: (path: string, v: any) => void }) {
  return (
    <SectionCard
      title="Database"
      description="Any SQLAlchemy URL. SQLite works out of the box; switch to Postgres for production."
    >
      <Field label="Database URL">
        <TextInput value={draft.database?.url} onChange={(v) => set('database.url', v)} />
      </Field>
    </SectionCard>
  );
}

function AdvancedSection({
  text,
  setText,
  onApply,
  saving,
}: {
  text: string;
  setText: (v: string) => void;
  onApply: () => void;
  saving: boolean;
}) {
  return (
    <SectionCard
      title="Advanced — raw JSON patch"
      description="Paste a partial config object. Deep-merged into the current config and saved to config/config.yaml."
    >
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        className="input-field font-mono text-sm min-h-[260px]"
        placeholder='{"llm": {"provider": "openai"}}'
      />
      <button
        onClick={onApply}
        disabled={saving || !text.trim()}
        className="btn-primary flex items-center gap-2"
      >
        <Save size={16} />
        {saving ? 'Applying…' : 'Apply patch'}
      </button>
    </SectionCard>
  );
}
