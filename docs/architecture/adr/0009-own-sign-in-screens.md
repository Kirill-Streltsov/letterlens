# ADR-0009: Own sign-in screens on the web, hosted UI on iOS

Status: accepted · Date: 2026-11-26

## Context

The web app sent people to the Cognito hosted UI. On the Lite feature plan the
hosted UI is a plain white form. It does not look like LetterLens, it is English
only, and its error texts are technical. The sign-in screen is the first screen
a new user sees. The branded "managed login" needs the Essentials plan.

## Decision

1. The web app draws its own screens: sign in, create account, confirm email,
   forgot password, authenticator code (MFA) and "new password required".
2. The screens call the public Cognito user-pool API (`web/src/lib/cognito.ts`):
   `InitiateAuth` with `USER_PASSWORD_AUTH`, `SignUp`, `ConfirmSignUp`,
   `ResendConfirmationCode`, `ForgotPassword`, `ConfirmForgotPassword`,
   `RespondToAuthChallenge`, `REFRESH_TOKEN_AUTH` and `RevokeToken`.
3. The web client has no OAuth settings and no callback URLs.
   It allows only `USER_PASSWORD_AUTH` and `REFRESH_TOKEN_AUTH`.
4. The iOS app keeps the hosted UI with PKCE in `ASWebAuthenticationSession`.

## Alternatives

| Option | Why not |
| --- | --- |
| Hosted UI with CSS | The Lite plan allows only a few CSS classes; no logo in CloudFormation |
| Managed login (Essentials plan) | Costs money above the free tier and still looks like Cognito |
| SRP (`USER_SRP_AUTH`) | Needs a large library or own big-number code; the password still only goes to Cognito over TLS |

## Consequences

- The password goes from the browser to `cognito-idp.<region>.amazonaws.com` over TLS.
  It never reaches the LetterLens API, the logs or the database.
- Cognito still enforces the password policy, the lockout after failed attempts,
  email verification and "prevent user existence errors". The screen shows one
  message for "wrong password" and "no such account".
- The password rules exist twice: in the user pool and in `passwordProblems()`.
  A test keeps the web rules equal to the policy in the stack.
- Sign-out revokes the refresh token on the server.
- The web app has no "Sign in with Google/Apple". Social sign-in would need the hosted UI again.
