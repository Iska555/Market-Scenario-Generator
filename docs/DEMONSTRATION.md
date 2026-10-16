# Original synthetic demonstration v1

This is an isolated research example: **Demonstration portfolio — synthetic data;
no real money invested**. There is no Lightyear account, statement, broker execution
or verified personal track record. Paper operation and actual-account reconciliation
remain separate future histories. Nothing is published by loading the example.

## Deliberate setup

In the private Ledger, choose synthetic demonstration mode, give it a separate UUID
and create the empty GBP portfolio. Click **Load original synthetic example**.
Reloading an unchanged example is idempotent. The loader refuses a legacy/unclassified
portfolio, another currency, or a demo with unrelated existing transactions. It never
resets or overwrites history. Each demo has its own fictional security namespace,
ledger, thesis versions and immutable load receipt.

In Performance, select that demo and click **Load demo evidence with contribution
and synthetic comparison**. Inspect the supplied inputs, then choose **Measure
recorded performance**. Loading evidence selects those reports but does not calculate,
publish, adopt an expected-return view or make an investment decision. Private replay
downloads remain private. Later public downloads require a separate allowlist.

For a CLI workflow after explicit migrations, provide DATABASE_URL privately and use
a fresh output directory:

```powershell
backend/.venv/Scripts/python.exe scripts/load_demo.py --portfolio-id <new-demo-uuid> --create --output <new-private-output-directory>
```

Placeholders above must be replaced. Omit `--create` when deliberately reloading
the same existing demo. Keep the creation name identical on retries. The script
rejects a nonempty output directory to preserve previous artifacts. It produces
private performance/contribution/comparison JSON, input evidence, fixture, receipt,
compatible backend source and a hash/runtime manifest. It is not a database backup,
deployment package, external timestamp or public-safe bundle.

## Original fixture and dates

The versioned source is `backend/demo/launch_v1.json`. It is wholly original and
fictional. The sample covers **20 December 2025–5 February 2026**, 48 UTC daily
closing values and 47 return intervals. It was chosen to cover difficult workflows
and a negative TWR, not to make performance attractive. Both years are partial;
January is the only full calendar month. Annualized TWR is unavailable for this
short sample. Short-window XIRR and descriptive risk ratios need their visible
sample-context warnings; they are not estimates of persistent skill.

Fictional Harbor Workshop (GBP) and Orchard Systems (USD) are ordinary equity
identities, not funds or real securities. Inputs cover funding, purchases, partial
sale, a closed loser, net dividends, fees, GBP/USD conversion, a later deposit,
withdrawal and an erroneous fee reversed and replaced. All 13 immutable events,
including the losing position and correction, remain in the full ledger.

Synthetic price, FX and comparison levels interpolate the explicitly supplied
anchors on UTC calendar days using Decimal, six decimal places and half-even
rounding. Within a synthetic day, the quote/FX is deliberately flat; external-flow
marks use the same declared point immediately before the flow. This is a synthetic
input-generation policy, not real-market gap filling, a market calendar, provider
price discovery or synchronized real-market evidence. Unadjusted prices, booked
net dividends/fees, exact flow marks and zero quote-age allowance are explicit.

Fixture-effective dates and actual `recorded_at`, thesis/review creation,
receipt `loaded_at` and any later public publication timestamp are distinct.
Original example thesis and review narratives describe fictional dates in their
notes. Their server timestamps are the actual current creation times. They do
not assert the owner knew or acted on those beliefs in the past.

Benchmark contract `published_at`/`retrieved_at` fields use the actual load time:
the constructed synthetic input became available then. They do not mean the
application published a public snapshot at that time or that a historical market
index/provider existed. The comparison is an original synthetic illustration,
not an investable or endorsed benchmark. No third-party redistribution rights
are needed for these wholly original inputs.

## Independent economic checks

Final balances: GBP **6,154** and USD **2,100**, plus 40 Harbor shares at GBP 66.
Harbor moving-average local cost is GBP 2,404. At declared GBP/USD 0.82, final
NAV is 6,154 + 40×66 + 2,100×0.82 = **GBP 10,516**.

Orchard's fully closed local net example loss is -20×100 - 5 + 10 + 20×80 - 5 =
**USD -400**. This local position P&L is distinct from its geometrically linked
portfolio return contribution and FX effects. The mistaken GBP 9 fee is reversed;
the corrected GBP 2 fee remains active.

The opening daily NAV is GBP 10,000. The first invested close has declared
GBP/USD 0.79875 and NAV 4,993 + 3,000 + 2,495×0.79875 = **GBP 9,985.88125**.
Its return is **-0.001411875**. The engines independently handle later flows and
geometric linking; final NAV minus net funding is not substituted for TWR.

Supplied assumptions and evidence remain explicit. Missing marks, invalid FX and
incomplete comparison coverage fail or remain typed unavailable; no reduced sample
or zero-filled history is used. Changing ledger/research/security identity after
load invalidates reuse of the original fixture receipt. A new example revision
requires a separate demo identity, not relabelling existing history.

## Replay and archive boundary

Use the three existing replay CLIs on their corresponding raw private JSON files.
Matching source/runtime is required, including exact source bytes. The original
fixture is retained separately and hashed, while normal report manifests retain
their accepted schemas. Archived source exports contain backend Python, the original
fixture and replay/loader entry points; they exclude migrations, database backups,
installed dependencies, frontend and hosting. No old report/hash/archive is rewritten
to make it replay under this new source. Public projection/publication, restore and
deployment are subsequent gates in PLAN.md.
