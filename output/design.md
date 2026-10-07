# Design polish (Problem 10)

**Direction: "Old Campus storefront."** The site keeps its Yale blue, and the rest of the design draws on two things a Campus Customs shopper knows: the warm stone of New Haven's college buildings and the details of collegiate apparel (stripes, crests, pennants). Every new element repeats one of a few shapes, so the shop reads as one brand rather than a template.

## What changed

**Type, color and spacing** (`frontend/src/index.css`, `frontend/index.html`)
- **Fonts:**
  - Headings, product names and the wordmark use Fraunces, a classic serif with some warmth. Section titles are now in sentence case instead of the old all-caps sans, so they read like a shop sign rather than a form.
  - Body text and controls use Source Sans 3 at 17 px, up from 16.
  - Small uppercase letter-spaced labels stay for categories and section labels, as a varsity touch.
- **Colors:**
  - Yale blue (#00356b) stays the main color, with a deeper navy for the hero, footer and chat header.
  - The cool grays are replaced by warm limestone neutrals (#f5f1e9 and lighter) for bands and panels.
  - Stock colors are used the same way everywhere: green for in stock, orange for "only a few left", gray and struck through for sold out.
- **Spacing and shape:** a wider page (1,240 px), more room between sections (88 px), 16 px card corners, pill-shaped buttons and search field, and soft blue-tinted shadows.

**Distinctive touches**
- **Varsity double stripe** (two thin parallel rules, like the stripe on a rugby shirt). It appears:
  - under the header, above every section title, and along the top of the login card;
  - at the bottom of the hero and the chat header;
  - down the edge of the "Find your corner of Yale" cards and the About list;
  - sliding in under a product card when you point at it.
- **CC shield monogram:** the logo, the footer brand, the chat assistant's avatar, the top of the login and sign-up cards, a faint watermark on the "Visit the shop" card, and the favicon. It is the shop's own mark, not Yale's shield.
- **Pennant labels** on the home page's category tiles, which turn lighter blue and extend when hovered.
- **The hero shows real products as tilted photo prints.** Each print carries its name and price, drifts slowly, and straightens when you point at it. The headline ends in an italic sky-blue *every day.*
- **Fine diagonal pinstripes** on navy and stone panels: the hero, the page headers, the About banner, the visit card and the footer.

**Product cards:** serif names, plus a row of XS–XXL size boxes on every card: orange means only a few left, crossed out means sold out. With the size filter on, the chosen size is filled in, alongside the existing "Size M: Only 5 left" line. Pointing at a card lifts it, slowly zooms the photo and slides in the stripe.

**Product pages:**
- The photo sits in a framed panel that stays in view while you scroll (desktop) and zooms slowly on hover.
- The name is in serif. The price sits beside a "Your size" chip (green, orange or gray).
- Each color name has a swatch dot.
- Each size box has a small stock bar: full at 20 or more, orange when 5 or fewer are left.
- Under the buttons, a short reassurance list: officially licensed, try it on at 57 Broadway, and stock shown for every size.

**Chat panel:**
- A navy header with the monogram avatar and the stripe, and messages on a stone background in rounded bubbles.
- Product cards in replies highlight when hovered, and the "Showing N products" link is now a pill.
- The panel pops up from its button, and suggested questions fade in one after another.
- The chat button has a white ring, so it stays visible over the navy footer.

**Motion** (short and soft, and all switched off when a device asks for reduced motion):
- Pages rise in as you arrive, and the hero prints drift.
- Cards lift when you point at them, nav underlines grow, and arrows nudge in the direction they point.
- Stock bars fill when a product page opens, and chat messages rise in.

**Phones (375 px):** no sideways scrolling. Hero and action buttons go full width. Category chips scroll sideways instead of stacking four rows deep. The size filter wraps into two neat rows, cards stay two across with a compact size row, and the chat opens full width.

I also corrected one stale sentence on the About page: it said the chat assistant was "on its way". It now says the assistant can check sizes and stock.

## Why this should help customers explore and feel confident

- **Real products from the first screen.** The hero prints show actual items with prices, one click from their pages. Pennant categories and the "corner of Yale" cards give easy next steps, and hover feedback makes it clear what's clickable.
- **Availability before you click.** The size boxes on every card and the stock bars on product pages show at a glance what's left in your size, so fewer clicks end on a sold-out size.
- **It looks like an established, local shop.**
  - One monogram, one blue and one stripe used consistently suggest a real brand.
  - The reassurance list repeats the facts that matter: licensed, a physical shop at 57 Broadway, and live stock.
  - The serif headings and stone tones give a collegiate feel that fits Yale gear.
- **Honest and readable.** Product photos are the originals and fill their frames as before. Prices and stock come straight from the database. Body text is larger, with high-contrast colors.

## Checks

- **Desktop (1280 × 800) and phone (375 × 812):** viewed in the browser for home, Products (with the size filter), product pages (with and without a chosen size), chat search results, the chat panel, login and About. The phone menu was also checked, and no page scrolls sideways at 375 px.
- **Existing features still work:**
  - The size filter shows 80 of 102 products in size M.
  - A chat search ("What hoodies do you have?") opened the 27-hoodie results page, and its first card opened that product.
  - Logging in as the Problem 4 test account brought back the saved conversation (30 messages, "Welcome back, Bulldog!"), and logging out cleared it.
  - `check_auth.py` passes 21 of 21 and `check_tools.py` 30 of 30. `npm run lint` and `npm run build` are clean.
- **Data:** the backend code, the database (catalogue and inventory compared with the copy from before Problem 4) and the 102 product photos are unchanged.
