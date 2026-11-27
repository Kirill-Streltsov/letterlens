import { CognitoClient, CognitoError, passwordProblems } from "@/lib/cognito";

type Call = { url: string; target: string; body: Record<string, unknown> };

function fakeFetch(responses: Array<{ status?: number; json: unknown }>) {
  const calls: Call[] = [];
  const impl = (async (url: string, init: RequestInit) => {
    const headers = init.headers as Record<string, string>;
    calls.push({ url, target: headers["X-Amz-Target"]!, body: JSON.parse(String(init.body)) });
    const next = responses.shift() ?? { json: {} };
    return new Response(JSON.stringify(next.json), { status: next.status ?? 200 });
  }) as unknown as typeof fetch;
  return { calls, impl };
}

describe("Cognito client", () => {
  it("signs in with the password flow and returns tokens", async () => {
    const { calls, impl } = fakeFetch([
      { json: { AuthenticationResult: { AccessToken: "a", RefreshToken: "r", ExpiresIn: 3600 } } },
    ]);
    const step = await new CognitoClient("eu-central-1", "client-1", impl).signIn("a@b.de", "secret12345");
    expect(step).toEqual({ kind: "done", result: { accessToken: "a", refreshToken: "r", expiresIn: 3600 } });
    expect(calls[0]!.url).toBe("https://cognito-idp.eu-central-1.amazonaws.com/");
    expect(calls[0]!.target).toBe("AWSCognitoIdentityProviderService.InitiateAuth");
    expect(calls[0]!.body).toEqual({
      ClientId: "client-1",
      AuthFlow: "USER_PASSWORD_AUTH",
      AuthParameters: { USERNAME: "a@b.de", PASSWORD: "secret12345" },
    });
  });

  it("asks for the authenticator code when MFA is on", async () => {
    const { impl } = fakeFetch([{ json: { ChallengeName: "SOFTWARE_TOKEN_MFA", Session: "s1" } }]);
    const step = await new CognitoClient("eu-central-1", "c", impl).signIn("a@b.de", "x");
    expect(step).toEqual({ kind: "mfa", session: "s1" });
  });

  it("maps service errors to messages for people, without saying whether the account exists", async () => {
    const { impl } = fakeFetch([
      { status: 400, json: { __type: "NotAuthorizedException", message: "Incorrect username or password." } },
      { status: 400, json: { __type: "com.amazonaws#UserNotFoundException" } },
    ]);
    const client = new CognitoClient("eu-central-1", "c", impl);
    const wrong = await client.signIn("a@b.de", "x").catch((e: CognitoError) => e);
    const missing = await client.signIn("b@b.de", "x").catch((e: CognitoError) => e);
    expect(wrong).toBeInstanceOf(CognitoError);
    expect((wrong as CognitoError).code).toBe("NotAuthorizedException");
    expect((missing as CognitoError).code).toBe("UserNotFoundException");
    expect((wrong as CognitoError).message).toBe((missing as CognitoError).message);
  });

  it("keeps the old refresh token when Cognito does not send a new one", async () => {
    const { calls, impl } = fakeFetch([{ json: { AuthenticationResult: { AccessToken: "a2", ExpiresIn: 3600 } } }]);
    const result = await new CognitoClient("eu-central-1", "c", impl).refresh("r1");
    expect(result.refreshToken).toBe("r1");
    expect(calls[0]!.body.AuthFlow).toBe("REFRESH_TOKEN_AUTH");
  });

  it("reports a network failure as such", async () => {
    const impl = (async () => {
      throw new TypeError("Failed to fetch");
    }) as unknown as typeof fetch;
    const error = await new CognitoClient("eu-central-1", "c", impl).forgotPassword("a@b.de").catch((e: CognitoError) => e);
    expect((error as CognitoError).code).toBe("NetworkError");
  });

  it("signs up with the email as user name", async () => {
    const { calls, impl } = fakeFetch([{ json: { UserConfirmed: false, UserSub: "u" } }]);
    expect(await new CognitoClient("eu-central-1", "c", impl).signUp("a@b.de", "secret12345")).toEqual({ confirmed: false });
    expect(calls[0]!.body).toMatchObject({ Username: "a@b.de", UserAttributes: [{ Name: "email", Value: "a@b.de" }] });
  });
});

describe("password rules", () => {
  it("match the user pool policy: 10 characters and a digit", () => {
    expect(passwordProblems("short1")).toEqual(["at least 10 characters"]);
    expect(passwordProblems("longenoughpassword")).toEqual(["at least one digit"]);
    expect(passwordProblems("longenough1")).toEqual([]);
  });
});
