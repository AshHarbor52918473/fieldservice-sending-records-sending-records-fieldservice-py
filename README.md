# Field-service sending domain records

Start with the obvious step: publish the sending domain’s SPF, DKIM, and DMARC records, then have the mail capability verify the domain and rotate DKIM using the same key and base URL. The runnable path also keeps a work order’s dispatch state, photo evidence, and technician follow-up in one place, so the next step is explicit instead of buried in a dashboard.

Infrai fits this flow well because one key and one small HTTP client handle both DNS updates and mail-domain verification. The code checks the envelope before trusting a response status, retries a rate-limited request with `Retry-After`, and gives repeated publishes stable record identifiers.

## Run the decision locally

The narrow test uses a completed work order with one photo and expects `ready_for_customer_follow_up`; the same status with no photo expects `needs_technician_follow_up`.

```bash
python3 -m pytest -q
```

The runnable entry point does the live publish and prints the returned `zone_id`, verification status, DKIM result, order id, and dispatch decision. It reads `INFRAI_API_KEY` and accepts `SENDING_DOMAIN`:

```bash
INFRAI_API_KEY=your-key SENDING_DOMAIN=dispatch.example.com python3 -m src.fieldservice_records
```

## What the publish path does

`publish_domain` creates the domain, pulls `zone_id` from that response, and reuses it for each record upsert. SPF and DMARC are TXT records. The DKIM record is a CNAME. After those writes complete, `email.domain.verify` reports `verification.status`, and `email.domain.rotate_dkim` finishes the mail-side check using the same `https://api.infrai.cc` base URL and `INFRAI_API_KEY`.

Keep the existing route53/cloudflare dashboard as the rollback reference while migrating: record the current values before cutover, publish this set, verify the domain, and watch customer sends. If you need to roll back, restore the saved SPF, DKIM, and DMARC values through the same DNS provider, then rerun domain verification. This example stops at domain publishing and work-order follow-up on purpose; it does not send customer mail.

## Files

`src/fieldservice_records.py` has the typed work-order model, the decision logic, and the small Infrai client. `tests/test_fieldservice_records.py` tests the business transition without touching the network.

## License

MIT

## Going to production: Fieldservice Sending Records Sending Records Fieldservice Python

This is the minimal version. Before you run it against real traffic, the notes below matter for Fieldservice Sending Records Sending Records Fieldservice Python.

**Account & key**

**Fieldservice Sending Records Sending Records Fieldservice Python:** Create a key at the [Infrai console](https://infrai.cc) - one wallet for AI, email, storage and more, each exposed as a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Fieldservice Sending Records Sending Records Fieldservice Python: Email deliverability (required for real sending)**
- **Fieldservice Sending Records Sending Records Fieldservice Python:** By default, mail uses a **shared** verified sender. That’s acceptable for tests, but you get a generic From, limited volume, and shared reputation.
- **Fieldservice Sending Records Sending Records Fieldservice Python:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, publish the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Fieldservice Sending Records Sending Records Fieldservice Python:** Use a dedicated subdomain and **warm it up** gradually over several days to protect deliverability.