# Securing webhooks

The shared standard requires authenticated delivery and verified outcomes.
HMAC is a recommended implementation when the sender supports it, not a universal
requirement. These instructions reach opted-in developers when they update their
shared guidance; they are not an automatic scanner or proof that an endpoint is safe.

| Provider capability | Suggested control | Limit to record |
| --- | --- | --- |
| Signed payload | Verify the provider's signature on exact raw bytes using its documented algorithm | Signatures alone do not prevent replay |
| OAuth/JWT, mTLS or authenticated header | Validate credentials, issuer/audience or client certificate as applicable | A static bearer token does not independently sign the body |
| Only a secret in the callback URL | Owner-approved exception, high-entropy secret, rotation and URL/log redaction; network restrictions where approved | URLs can leak through access logs; this is not equivalent to payload signing |
| No usable authentication | Agree a supported control or explicitly review the risk before exposure | Do not silently accept unauthenticated side effects |

## HMAC examples

For a sender whose documented input is `timestamp + "." + raw_body`, verify that
signature and enforce its timestamp window. Repeated delivery inside the window
still needs idempotent processing or durable deduplication.

GitHub uses `X-Hub-Signature-256` and HMAC-SHA256 over the raw body, without that
timestamp prefix. Compare with `hmac.compare_digest` before decoding or acting on
the payload. Reject empty secrets and invalid signatures. See
[GitHub's verification specification](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries).

The portfolio catalogue worker treats a signed event as a request to re-read public
GitHub metadata. It does not copy event content into the README. Duplicate delivery
produces no new commit when the catalogue is unchanged, and the file SHA prevents
overwriting a concurrent update. This makes reconciliation idempotent; it is not
a general replay cache for payment, deployment or ingestion triggers.

## Acceptance evidence

Exercise invalid credentials, body tampering, provider-specific timestamp rules,
wrong tenants/installations and duplicate delivery before merge. Assert that rejected
requests cause no queue or downstream action. For a token-only provider, do not
claim a tampered-body test proves signature validation it cannot perform.

After the approved CI deployment, record the deployed revision, a rejected request,
a genuine provider delivery and its observed downstream result. Test replay and
recovery against the side effect being protected. Keep credentials and sensitive
payloads out of that evidence.
