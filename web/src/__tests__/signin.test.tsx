import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import { resetConfigForTests } from "@/lib/config";

const replace = vi.fn();
let search = new URLSearchParams();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  useSearchParams: () => search,
}));

const { default: SignInPage } = await import("@/app/signin/page");

const CONFIG = { apiBase: "", stage: "prod", region: "eu-central-1", userPoolId: "p", clientId: "c", authDomain: "" };

/** Serves /config.json and answers Cognito calls in order; records the Cognito operations. */
function mockNetwork(cognito: Array<{ status?: number; json: unknown }>) {
  const ops: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      if (url === "/config.json") return new Response(JSON.stringify(CONFIG));
      ops.push((init?.headers as Record<string, string>)["X-Amz-Target"]!.split(".")[1]!);
      const next = cognito.shift() ?? { json: {} };
      return new Response(JSON.stringify(next.json), { status: next.status ?? 200 });
    }),
  );
  return ops;
}

beforeEach(() => {
  sessionStorage.clear();
  resetConfigForTests();
  replace.mockReset();
  search = new URLSearchParams();
});

afterEach(() => vi.unstubAllGlobals());

describe("sign-in screen", () => {
  it("creates an account, confirms the email and signs in without asking for the password again", async () => {
    search = new URLSearchParams("mode=signup");
    const ops = mockNetwork([
      { json: { UserConfirmed: false } },
      { json: {} },
      { json: { AuthenticationResult: { AccessToken: "token", RefreshToken: "r", ExpiresIn: 3600 } } },
    ]);
    render(<SignInPage />);
    expect(await screen.findByRole("heading", { name: "Create your account" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: " Ana@Example.org " } });
    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "longenough1" } });
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByRole("heading", { name: "Check your email" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Code from the email"), { target: { value: "12 34 56" } });
    expect(screen.getByLabelText("Code from the email")).toHaveValue("123456");
    fireEvent.click(screen.getByRole("button", { name: "Confirm email" }));

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/letters/"));
    expect(ops).toEqual(["SignUp", "ConfirmSignUp", "InitiateAuth"]);
    expect(JSON.parse(sessionStorage.getItem("letterlens.auth")!).accessToken).toBe("token");
  });

  it("checks the password rules before it calls Cognito", async () => {
    search = new URLSearchParams("mode=signup");
    const ops = mockNetwork([]);
    render(<SignInPage />);
    fireEvent.change(await screen.findByLabelText("Email address"), { target: { value: "a@b.de" } });
    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "short" } });
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("at least 10 characters");
    expect(ops).toEqual([]);
  });

  it("shows one message for a wrong password and an unknown account", async () => {
    mockNetwork([{ status: 400, json: { __type: "NotAuthorizedException" } }]);
    render(<SignInPage />);
    fireEvent.change(await screen.findByLabelText("Email address"), { target: { value: "a@b.de" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "whatever123" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("The email address or the password is not correct.");
    expect(replace).not.toHaveBeenCalled();
  });

  it("sends an unconfirmed account to the code step", async () => {
    const ops = mockNetwork([{ status: 400, json: { __type: "UserNotConfirmedException" } }, { json: {} }]);
    render(<SignInPage />);
    fireEvent.change(await screen.findByLabelText("Email address"), { target: { value: "a@b.de" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "longenough1" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("heading", { name: "Check your email" })).toBeInTheDocument();
    expect(ops).toEqual(["InitiateAuth", "ResendConfirmationCode"]);
  });

  it("resets a forgotten password and signs in", async () => {
    const ops = mockNetwork([
      { json: {} },
      { json: {} },
      { json: { AuthenticationResult: { AccessToken: "t", ExpiresIn: 3600 } } },
    ]);
    render(<SignInPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Forgot password?" }));
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "a@b.de" } });
    fireEvent.click(screen.getByRole("button", { name: "Send code" }));
    expect(await screen.findByRole("heading", { name: "Choose a new password" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Code from the email"), { target: { value: "654321" } });
    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "newpassword9" } });
    fireEvent.click(screen.getByRole("button", { name: "Save password and sign in" }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/letters/"));
    expect(ops).toEqual(["ForgotPassword", "ConfirmForgotPassword", "InitiateAuth"]);
  });
});
