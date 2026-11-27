/**
 * A small client for the public Amazon Cognito user-pool API (JSON over HTTPS).
 *
 * The web app uses it to draw its own sign-in and sign-up screens instead of the hosted UI.
 * Only unauthenticated operations are used; no AWS credentials are needed. The password goes
 * over TLS to Cognito only, never to the LetterLens API.
 */

export interface AuthResult {
  accessToken: string;
  refreshToken?: string;
  expiresIn: number;
}

/** Sign-in either finishes or asks for one more step. */
export type SignInStep =
  | { kind: "done"; result: AuthResult }
  | { kind: "mfa"; session: string }
  | { kind: "new_password"; session: string };

export type CognitoErrorCode =
  | "NotAuthorizedException"
  | "UserNotConfirmedException"
  | "UsernameExistsException"
  | "CodeMismatchException"
  | "ExpiredCodeException"
  | "InvalidPasswordException"
  | "InvalidParameterException"
  | "LimitExceededException"
  | "TooManyRequestsException"
  | "TooManyFailedAttemptsException"
  | "PasswordResetRequiredException"
  | "UserNotFoundException"
  | "NetworkError"
  | "Unknown";

export class CognitoError extends Error {
  constructor(
    readonly code: CognitoErrorCode,
    message: string,
  ) {
    super(message);
    this.name = "CognitoError";
  }
}

const KNOWN = new Set<string>([
  "NotAuthorizedException",
  "UserNotConfirmedException",
  "UsernameExistsException",
  "CodeMismatchException",
  "ExpiredCodeException",
  "InvalidPasswordException",
  "InvalidParameterException",
  "LimitExceededException",
  "TooManyRequestsException",
  "TooManyFailedAttemptsException",
  "PasswordResetRequiredException",
  "UserNotFoundException",
]);

/** Messages for people, not for developers. Cognito's own texts are technical and English-only. */
export function friendlyMessage(code: CognitoErrorCode): string {
  switch (code) {
    case "NotAuthorizedException":
    case "UserNotFoundException":
      return "The email address or the password is not correct.";
    case "UsernameExistsException":
      return "An account with this email address already exists. Sign in instead.";
    case "CodeMismatchException":
      return "The code is not correct. Check the newest email from us.";
    case "ExpiredCodeException":
      return "The code has expired. Ask for a new one.";
    case "InvalidPasswordException":
      return "Choose a password with at least 10 characters and at least one digit.";
    case "InvalidParameterException":
      return "Please check the email address and the password.";
    case "LimitExceededException":
    case "TooManyRequestsException":
    case "TooManyFailedAttemptsException":
      return "Too many attempts. Wait a few minutes, then try again.";
    case "PasswordResetRequiredException":
      return "You must set a new password. Use “Forgot password”.";
    case "UserNotConfirmedException":
      return "Confirm your email address first. We sent you a code.";
    case "NetworkError":
      return "No connection. Check your internet connection and try again.";
    default:
      return "Something went wrong. Please try again.";
  }
}

export class CognitoClient {
  constructor(
    private readonly region: string,
    private readonly clientId: string,
    private readonly fetchImpl: typeof fetch = (...args) => fetch(...args),
  ) {}

  private async call<T>(operation: string, body: Record<string, unknown>): Promise<T> {
    let response: Response;
    try {
      response = await this.fetchImpl(`https://cognito-idp.${this.region}.amazonaws.com/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-amz-json-1.1",
          "X-Amz-Target": `AWSCognitoIdentityProviderService.${operation}`,
        },
        body: JSON.stringify({ ClientId: this.clientId, ...body }),
      });
    } catch {
      throw new CognitoError("NetworkError", friendlyMessage("NetworkError"));
    }
    const json = (await response.json().catch(() => ({}))) as Record<string, unknown>;
    if (!response.ok) {
      // The type is "Name" or "aws.prefix#Name".
      const raw = String(json.__type ?? response.headers.get("x-amzn-errortype") ?? "");
      const name = raw.split("#").pop()?.split(":")[0] ?? "";
      const code = (KNOWN.has(name) ? name : "Unknown") as CognitoErrorCode;
      throw new CognitoError(code, friendlyMessage(code));
    }
    return json as T;
  }

  private static toStep(json: InitiateAuthResponse): SignInStep {
    const r = json.AuthenticationResult;
    if (r) {
      return {
        kind: "done",
        result: { accessToken: r.AccessToken, refreshToken: r.RefreshToken, expiresIn: r.ExpiresIn },
      };
    }
    if (json.ChallengeName === "SOFTWARE_TOKEN_MFA" && json.Session) return { kind: "mfa", session: json.Session };
    if (json.ChallengeName === "NEW_PASSWORD_REQUIRED" && json.Session) {
      return { kind: "new_password", session: json.Session };
    }
    throw new CognitoError("Unknown", friendlyMessage("Unknown"));
  }

  async signIn(email: string, password: string): Promise<SignInStep> {
    const json = await this.call<InitiateAuthResponse>("InitiateAuth", {
      AuthFlow: "USER_PASSWORD_AUTH",
      AuthParameters: { USERNAME: email, PASSWORD: password },
    });
    return CognitoClient.toStep(json);
  }

  async answerMfa(email: string, session: string, code: string): Promise<SignInStep> {
    const json = await this.call<InitiateAuthResponse>("RespondToAuthChallenge", {
      ChallengeName: "SOFTWARE_TOKEN_MFA",
      Session: session,
      ChallengeResponses: { USERNAME: email, SOFTWARE_TOKEN_MFA_CODE: code },
    });
    return CognitoClient.toStep(json);
  }

  async setNewPassword(email: string, session: string, password: string): Promise<SignInStep> {
    const json = await this.call<InitiateAuthResponse>("RespondToAuthChallenge", {
      ChallengeName: "NEW_PASSWORD_REQUIRED",
      Session: session,
      ChallengeResponses: { USERNAME: email, NEW_PASSWORD: password },
    });
    return CognitoClient.toStep(json);
  }

  async refresh(refreshToken: string): Promise<AuthResult> {
    const json = await this.call<InitiateAuthResponse>("InitiateAuth", {
      AuthFlow: "REFRESH_TOKEN_AUTH",
      AuthParameters: { REFRESH_TOKEN: refreshToken },
    });
    const step = CognitoClient.toStep(json);
    if (step.kind !== "done") throw new CognitoError("Unknown", friendlyMessage("Unknown"));
    return { ...step.result, refreshToken: step.result.refreshToken ?? refreshToken };
  }

  async signUp(email: string, password: string): Promise<{ confirmed: boolean }> {
    const json = await this.call<{ UserConfirmed?: boolean }>("SignUp", {
      Username: email,
      Password: password,
      UserAttributes: [{ Name: "email", Value: email }],
    });
    return { confirmed: Boolean(json.UserConfirmed) };
  }

  async confirmSignUp(email: string, code: string): Promise<void> {
    await this.call("ConfirmSignUp", { Username: email, ConfirmationCode: code });
  }

  async resendCode(email: string): Promise<void> {
    await this.call("ResendConfirmationCode", { Username: email });
  }

  async forgotPassword(email: string): Promise<void> {
    await this.call("ForgotPassword", { Username: email });
  }

  async confirmForgotPassword(email: string, code: string, password: string): Promise<void> {
    await this.call("ConfirmForgotPassword", { Username: email, ConfirmationCode: code, Password: password });
  }

  /** Ends the session on the server: the refresh token and the tokens made from it stop working. */
  async revoke(refreshToken: string): Promise<void> {
    await this.call("RevokeToken", { Token: refreshToken });
  }
}

interface InitiateAuthResponse {
  AuthenticationResult?: { AccessToken: string; RefreshToken?: string; ExpiresIn: number };
  ChallengeName?: string;
  Session?: string;
}

/** The same rules as the user pool's password policy (infra/letterlens_infra/stack.py). */
export function passwordProblems(password: string): string[] {
  const problems: string[] = [];
  if (password.length < 10) problems.push("at least 10 characters");
  if (!/\d/.test(password)) problems.push("at least one digit");
  return problems;
}
