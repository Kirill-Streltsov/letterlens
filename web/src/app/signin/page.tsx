"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, type ReactNode, Suspense, useEffect, useId, useRef, useState } from "react";

import { Logo } from "@/components/Brand";
import { cognito, isLocal, isSignedIn, signInAsDevUser, storeSession } from "@/lib/auth";
import { CognitoError, passwordProblems, type SignInStep } from "@/lib/cognito";
import { type AppConfig, loadConfig } from "@/lib/config";

type Step =
  | { name: "signin" }
  | { name: "signup" }
  | { name: "confirm" }
  | { name: "forgot" }
  | { name: "reset" }
  | { name: "mfa"; session: string }
  | { name: "new_password"; session: string };

const RESEND_COOLDOWN_S = 30;

/* ------------------------------------------------------------------ */
/* Brand panel                                                         */
/* ------------------------------------------------------------------ */

function Check() {
  return (
    <svg width="18" height="18" viewBox="0 0 20 20" aria-hidden="true">
      <circle cx="10" cy="10" r="9" fill="var(--marker)" />
      <path d="M6 10.5l2.6 2.5L14 7.5" fill="none" stroke="var(--ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** A small, made-up letter that shows what the product does: one line highlighted, explained, checked. */
function LetterDemo() {
  return (
    <div className="auth-demo" aria-hidden="true">
      <div className="auth-sheet" lang="de">
        <div className="auth-sheet-head">
          <span>Finanzamt Musterstadt</span>
          <span>02.12.2026</span>
        </div>
        <div className="auth-sheet-title">Bescheid über Einkommensteuer 2025</div>
        <div className="auth-sheet-bar" style={{ width: "92%" }} />
        <div className="auth-sheet-bar" style={{ width: "78%" }} />
        <div className="auth-sheet-line hl">Bitte zahlen Sie 312,00 € bis zum 15.01.2027.</div>
        <div className="auth-sheet-bar" style={{ width: "85%" }} />
        <div className="auth-sheet-bar" style={{ width: "60%" }} />
      </div>
      <div className="auth-explain">
        <div className="auth-explain-text">You must pay €312.00 to the tax office by 15 January 2027.</div>
        <div className="row" style={{ gap: 8 }}>
          <span className="pill ok">Found in the letter</span>
          <span className="pill">15 Jan 2027</span>
        </div>
      </div>
    </div>
  );
}

function BrandPanel() {
  return (
    <aside className="auth-aside">
      <Link href="/" className="brand">
        <Logo /> LetterLens
      </Link>
      <div className="auth-aside-body">
        <h2 className="auth-aside-title">
          Official post,
          <br />
          in <mark>plain words</mark>.
        </h2>
        <LetterDemo />
        <ul className="auth-points">
          <li>
            <Check /> Summaries in English, Turkish, Arabic, Ukrainian, Russian or plain German
          </li>
          <li>
            <Check /> Dates and amounts are checked against the letter itself
          </li>
          <li>
            <Check /> Each account&apos;s letters are encrypted with their own key; delete them at any time
          </li>
        </ul>
      </div>
      <p className="auth-aside-foot">General information, not legal advice.</p>
    </aside>
  );
}

/* ------------------------------------------------------------------ */
/* Form parts                                                          */
/* ------------------------------------------------------------------ */

function Field({
  label,
  hint,
  children,
  id,
}: {
  label: string;
  hint?: ReactNode;
  children: ReactNode;
  id: string;
}) {
  return (
    <div className="auth-field">
      <label htmlFor={id}>{label}</label>
      {children}
      {hint && <div className="auth-hint">{hint}</div>}
    </div>
  );
}

function PasswordInput({
  id,
  value,
  onChange,
  autoComplete,
}: {
  id: string;
  value: string;
  onChange: (v: string) => void;
  autoComplete: "current-password" | "new-password";
}) {
  const [shown, setShown] = useState(false);
  return (
    <div className="auth-password">
      <input
        id={id}
        type={shown ? "text" : "password"}
        value={value}
        autoComplete={autoComplete}
        required
        onChange={(e) => onChange(e.target.value)}
      />
      <button type="button" className="auth-reveal" onClick={() => setShown((s) => !s)} aria-pressed={shown}>
        {shown ? "Hide" : "Show"}
      </button>
    </div>
  );
}

function PasswordRules({ password }: { password: string }) {
  const problems = passwordProblems(password);
  const rules = ["at least 10 characters", "at least one digit"];
  return (
    <ul className="auth-rules" aria-label="Password rules">
      {rules.map((r) => {
        const ok = password.length > 0 && !problems.includes(r);
        return (
          <li key={r} className={ok ? "ok" : undefined}>
            <span aria-hidden="true">{ok ? "✓" : "•"}</span> {r}
            <span className="sr-only">{ok ? " (done)" : " (missing)"}</span>
          </li>
        );
      })}
    </ul>
  );
}

function CodeInput({ id, value, onChange }: { id: string; value: string; onChange: (v: string) => void }) {
  return (
    <input
      id={id}
      className="auth-code"
      inputMode="numeric"
      autoComplete="one-time-code"
      pattern="[0-9]{6}"
      maxLength={6}
      required
      value={value}
      onChange={(e) => onChange(e.target.value.replace(/\D/g, "").slice(0, 6))}
    />
  );
}

/* ------------------------------------------------------------------ */
/* The flow                                                            */
/* ------------------------------------------------------------------ */

function AuthForm({ initial }: { initial: "signin" | "signup" }) {
  const router = useRouter();
  const ids = useId();
  const [step, setStep] = useState<Step>(initial === "signup" ? { name: "signup" } : { name: "signin" });
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [cooldown, setCooldown] = useState(0);
  const headingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  const go = (next: Step, message: string | null = null) => {
    setStep(next);
    setError(null);
    setInfo(message);
    setCode("");
    // Move focus to the new heading so screen readers announce the step.
    requestAnimationFrame(() => headingRef.current?.focus());
  };

  const finish = (s: SignInStep) => {
    if (s.kind === "done") {
      storeSession(s.result);
      router.replace("/letters/");
    } else if (s.kind === "mfa") {
      go({ name: "mfa", session: s.session });
    } else {
      setPassword("");
      go({ name: "new_password", session: s.session }, "Please choose a new password for your account.");
    }
  };

  const run = async (action: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (e) {
      if (e instanceof CognitoError && e.code === "UserNotConfirmedException") {
        const client = await cognito();
        await client.resendCode(email).catch(() => undefined);
        setCooldown(RESEND_COOLDOWN_S);
        go({ name: "confirm" }, `Confirm your email address first. We sent a new code to ${email}.`);
      } else {
        setError(e instanceof Error ? e.message : "Something went wrong. Please try again.");
      }
    } finally {
      setBusy(false);
    }
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (busy) return;
    void run(async () => {
      const client = await cognito();
      const mail = email.trim().toLowerCase();
      switch (step.name) {
        case "signin":
          finish(await client.signIn(mail, password));
          break;
        case "signup": {
          if (passwordProblems(password).length) {
            setError("Choose a password with at least 10 characters and at least one digit.");
            return;
          }
          const { confirmed } = await client.signUp(mail, password);
          if (confirmed) finish(await client.signIn(mail, password));
          else {
            setCooldown(RESEND_COOLDOWN_S);
            go({ name: "confirm" });
          }
          break;
        }
        case "confirm":
          await client.confirmSignUp(mail, code);
          if (password) finish(await client.signIn(mail, password));
          else go({ name: "signin" }, "Your email address is confirmed. Sign in now.");
          break;
        case "forgot":
          await client.forgotPassword(mail);
          setPassword("");
          setCooldown(RESEND_COOLDOWN_S);
          go({ name: "reset" });
          break;
        case "reset":
          if (passwordProblems(password).length) {
            setError("Choose a password with at least 10 characters and at least one digit.");
            return;
          }
          await client.confirmForgotPassword(mail, code, password);
          finish(await client.signIn(mail, password));
          break;
        case "mfa":
          finish(await client.answerMfa(mail, step.session, code));
          break;
        case "new_password":
          if (passwordProblems(password).length) {
            setError("Choose a password with at least 10 characters and at least one digit.");
            return;
          }
          finish(await client.setNewPassword(mail, step.session, password));
          break;
      }
    });
  };

  const resend = () =>
    void run(async () => {
      const client = await cognito();
      if (step.name === "reset") await client.forgotPassword(email.trim().toLowerCase());
      else await client.resendCode(email.trim().toLowerCase());
      setCooldown(RESEND_COOLDOWN_S);
      setInfo(`We sent a new code to ${email}.`);
    });

  const tabs = step.name === "signin" || step.name === "signup";
  const title = {
    signin: "Welcome back",
    signup: "Create your account",
    confirm: "Check your email",
    forgot: "Reset your password",
    reset: "Choose a new password",
    mfa: "Two-step verification",
    new_password: "Choose a new password",
  }[step.name];
  const lead = {
    signin: "Sign in to see your letters and deadlines.",
    signup: "It is free. You only need an email address.",
    confirm: `We sent a 6-digit code to ${email}. It can take a minute to arrive.`,
    forgot: "Enter your email address. If an account exists, we send you a code.",
    reset: `Enter the code we sent to ${email} and your new password.`,
    mfa: "Enter the 6-digit code from your authenticator app.",
    new_password: "Your account needs a new password before you can continue.",
  }[step.name];
  const action = {
    signin: "Sign in",
    signup: "Create account",
    confirm: "Confirm email",
    forgot: "Send code",
    reset: "Save password and sign in",
    mfa: "Verify",
    new_password: "Save password",
  }[step.name];

  const showEmail = step.name === "signin" || step.name === "signup" || step.name === "forgot";
  const showPassword = step.name === "signin" || step.name === "signup" || step.name === "reset" || step.name === "new_password";
  const newPassword = step.name !== "signin";
  const showCode = step.name === "confirm" || step.name === "reset" || step.name === "mfa";

  return (
    <div className="auth-form">
      {tabs && (
        <div className="auth-tabs" role="tablist" aria-label="Account">
          {(["signin", "signup"] as const).map((t) => (
            <button
              key={t}
              type="button"
              role="tab"
              aria-selected={step.name === t}
              className={step.name === t ? "active" : undefined}
              onClick={() => {
                if (step.name !== t) go(t === "signup" ? { name: "signup" } : { name: "signin" });
                window.history.replaceState(null, "", t === "signup" ? "?mode=signup" : "?");
              }}
            >
              {t === "signin" ? "Sign in" : "Create account"}
            </button>
          ))}
        </div>
      )}

      <h1 ref={headingRef} tabIndex={-1} className="auth-title">
        {title}
      </h1>
      <p className="muted">{lead}</p>

      <div aria-live="polite">
        {error && (
          <p className="auth-alert" role="alert">
            {error}
          </p>
        )}
        {info && !error && <p className="auth-info">{info}</p>}
      </div>

      <form onSubmit={submit} className="auth-fields" noValidate={false}>
        {showEmail && (
          <Field id={`${ids}-email`} label="Email address">
            <input
              id={`${ids}-email`}
              type="email"
              autoComplete="email"
              inputMode="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </Field>
        )}
        {showCode && (
          <Field
            id={`${ids}-code`}
            label={step.name === "mfa" ? "Authenticator code" : "Code from the email"}
            hint={
              step.name !== "mfa" && (
                <button type="button" className="auth-link" onClick={resend} disabled={cooldown > 0 || busy}>
                  {cooldown > 0 ? `Send a new code in ${cooldown} s` : "Send a new code"}
                </button>
              )
            }
          >
            <CodeInput id={`${ids}-code`} value={code} onChange={setCode} />
          </Field>
        )}
        {showPassword && (
          <Field
            id={`${ids}-password`}
            label={newPassword ? "New password" : "Password"}
            hint={
              newPassword ? (
                <PasswordRules password={password} />
              ) : (
                <button type="button" className="auth-link" onClick={() => go({ name: "forgot" })}>
                  Forgot password?
                </button>
              )
            }
          >
            <PasswordInput
              id={`${ids}-password`}
              value={password}
              onChange={setPassword}
              autoComplete={newPassword ? "new-password" : "current-password"}
            />
          </Field>
        )}

        <button className="btn auth-submit" type="submit" disabled={busy}>
          {busy && <span className="auth-spinner" aria-hidden="true" />}
          {busy ? "Please wait…" : action}
        </button>
      </form>

      {step.name === "signup" && (
        <p className="faint auth-small">
          LetterLens explains letters in general terms. It does not give legal advice and does not replace a counselling
          service.
        </p>
      )}
      {!tabs && (
        <button type="button" className="auth-link auth-back" onClick={() => go({ name: "signin" })}>
          ← Back to sign in
        </button>
      )}
    </div>
  );
}

function DevForm() {
  const router = useRouter();
  const [user, setUser] = useState("demo-client");
  return (
    <form
      className="auth-form auth-fields"
      onSubmit={(e) => {
        e.preventDefault();
        signInAsDevUser(user, user.startsWith("counsellor") ? "counsellor" : "");
        router.replace("/letters/");
      }}
    >
      <h1 className="auth-title">Local demo</h1>
      <p className="muted">Local development has no passwords. Choose a demo user.</p>
      <Field id="dev-user" label="Sign in as" hint={<>Use <code>counsellor-anna</code> for the case inbox (after <code>make seed</code>).</>}>
        <input id="dev-user" value={user} onChange={(e) => setUser(e.target.value)} />
      </Field>
      <button className="btn auth-submit" type="submit">
        Continue
      </button>
    </form>
  );
}

function SignIn() {
  const params = useSearchParams();
  const router = useRouter();
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (isSignedIn()) {
      router.replace("/letters/");
      return;
    }
    loadConfig().then(setConfig).catch(() => setFailed(true));
  }, [router]);

  return (
    <div className="auth">
      <BrandPanel />
      <main className="auth-main">
        <div className="auth-mobile-brand">
          <Link href="/" className="brand">
            <Logo /> LetterLens
          </Link>
        </div>
        <div className="auth-card">
          {failed && (
            <p className="auth-alert" role="alert">
              The app could not load its settings. Reload the page.
            </p>
          )}
          {!config && !failed && <div className="skeleton" style={{ height: 320 }} aria-label="Loading" />}
          {config && (isLocal(config) ? <DevForm /> : <AuthForm initial={params.get("mode") === "signup" ? "signup" : "signin"} />)}
        </div>
      </main>
    </div>
  );
}

export default function SignInPage() {
  return (
    <Suspense>
      <SignIn />
    </Suspense>
  );
}
