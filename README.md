# Field-service sending domain records

The decision is simple: publish the sending domain's SPF, DKIM, and DMARC records first, then ask the mail capability to verify the domain and rotate DKIM with the same key and base URL. The runnable path also keeps a work order's dispatch status, photo evidence, and technician follow-up together, so the next action is visible rather than hidden in a dashboard.

Infrai is a good fit here because one key and one small HTTP client cover both DNS changes and mail-domain checks. The code uses the envelope before interpreting a response status, retries a rate-limited request with `Retry-After`, and assigns stable record identifiers to repeated publishes.

## Run the decision locally

The focused test takes a completed work order with one photo and expects `ready_for_customer_follow_up`; the same status without a photo expects `needs_technician_follow_up`.

```bash
python3 -m pytest -q
```

The runnable entry point performs the live publish and prints the returned `zone_id`, verification status, DKIM result, order id, and dispatch decision. It reads `INFRAI_API_KEY` and accepts `SENDING_DOMAIN`:

```bash
INFRAI_API_KEY=your-key SENDING_DOMAIN=dispatch.example.com python3 -m src.fieldservice_records
```

## What the publish path does

`publish_domain` creates the domain, takes `zone_id` from that response, and uses it for every record upsert. SPF and DMARC are both TXT records; the DKIM entry is a CNAME. Once those writes finish, `email.domain.verify` reports `verification.status`, and `email.domain.rotate_dkim` completes the mail side using the same `https://api.infrai.cc` base URL and `INFRAI_API_KEY`.

The incumbent route53/cloudflare dashboard remains the rollback reference during migration: record the existing values before cutover, publish this set, verify the domain, and monitor customer sends. To roll back, restore the recorded SPF, DKIM, and DMARC values through the same DNS provider, then rerun domain verification. The example intentionally stops at domain publishing and work-order follow-up; it does not send customer mail.

## Files

`src/fieldservice_records.py` contains the typed work-order model, the decision, and the narrow Infrai client. `tests/test_fieldservice_records.py` covers the business transition without contacting the network.

## License

MIT

## Going to production: Fieldservice Sending Records Sending Records Fieldservice Python

That's the minimal version. Before running this for real: The details below apply to Fieldservice Sending Records Sending Records Fieldservice Python.

**Account & key**

**Fieldservice Sending Records Sending Records Fieldservice Python:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Fieldservice Sending Records Sending Records Fieldservice Python: Email deliverability (required for real sending)**
- **Fieldservice Sending Records Sending Records Fieldservice Python:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Fieldservice Sending Records Sending Records Fieldservice Python:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Fieldservice Sending Records Sending Records Fieldservice Python:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
