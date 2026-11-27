# Own domain for the website

The site works without an own domain at `https://<id>.cloudfront.net`. An own domain
(for example `letterlens.de`) makes the address easy to read and to trust.

Cost: the domain only, about 5 to 10 EUR per year for `.de`. The certificate (ACM) and
CloudFront with an own domain cost nothing. Use the DNS of the registrar or the free
Cloudflare DNS; a Route 53 hosted zone costs 0.50 USD per month.

## 1. Register the domain (person)

Register the domain at a registrar. For `.de`, DENIC does not publish the owner's
address in WHOIS. A registrant outside Germany needs a German contact for service
("Zustellungsbevollmächtigter"); most registrars offer one.

## 2. Request the certificate (operator)

CloudFront accepts only certificates from `us-east-1`.

```bash
aws acm request-certificate --region us-east-1 --validation-method DNS \
  --domain-name letterlens.de --subject-alternative-names www.letterlens.de
aws acm describe-certificate --region us-east-1 --certificate-arn <arn> \
  --query 'Certificate.DomainValidationOptions[].ResourceRecord'
```

Add each validation record (type CNAME) at the DNS provider. The status changes to
`ISSUED` after some minutes.

## 3. Configure and deploy

In `infra/cdk.json`, stage `prod`:

```json
"domainNames": ["letterlens.de", "www.letterlens.de"],
"certificateArn": "arn:aws:acm:us-east-1:<account>:certificate/<id>"
```

Push to `main`. The deploy adds the names to CloudFront and sets the public URL.
The old `cloudfront.net` address keeps working, so the iOS app needs no change.

## 4. Point the names to CloudFront

The stack output `CloudFrontDomain` is the target.

| Name | Type | Value |
|---|---|---|
| `www` | CNAME | `<id>.cloudfront.net` |
| apex (`@`) | ALIAS, ANAME or flattened CNAME | `<id>.cloudfront.net` |

If the DNS provider has no ALIAS for the apex, forward the apex to `https://www.letterlens.de`
with the registrar's web forwarding, and put `www.letterlens.de` first in `domainNames`.

## 5. Check

```bash
curl -sI https://letterlens.de/ | head -1
curl -s https://letterlens.de/health
```
