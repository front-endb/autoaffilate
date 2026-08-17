# Privacy policy — Pin Pipeline (personal-use app)

This is a personal, single-user automation tool. It is not a public service —
no third party ever creates an account or authorizes this app.

## What data this app touches

- **Pinterest**: the app connects only to the developer's own Pinterest
  account via OAuth, to read/write boards and pins on that same account.
  No other Pinterest user's data is accessed.
- **Product feed data**: publicly available affiliate product listings
  (title, price, image URL, affiliate link) from the developer's own
  affiliate program account. No personal data of any third party is
  collected.
- **AI providers (Anthropic, Google Gemini, fal.ai)**: prompts and product
  descriptions are sent to these providers solely to generate pin text and
  images. No end-user personal data is sent — only product metadata.

## What this app does not do

- It does not collect, store, or share personal data belonging to anyone
  other than its single operator.
- It does not sell or transfer any data to third parties.
- It does not run on behalf of, or provide access to, any user other than
  the developer who deployed it.

## Data retention

Generated images, pin records, and a local deduplication log are stored
only on the operator's own machine, in a local SQLite database. Nothing is
transmitted anywhere except to the API providers listed above, and to
Pinterest itself when publishing a pin.

## Contact

Questions about this app can be directed to the repository owner listed on
its GitHub page.
