# What was fixed / improved

## Bugs / performance fixes
- `search_products()` and `get_similar_products()` in `recommendation.py` were
  reloading and re-cleaning the **entire 80,000-row CSV from scratch on every
  single interaction** (every search keystroke, filter change, or button
  click). Both functions now accept an optional `df` argument so `app.py` can
  pass in the already-cached dataframe instead. This cuts repeated work
  significantly (confirmed by timing it against the real dataset).
- `app.py` was updated to pass its cached `df` into both functions.
- Removed the unused/legacy `data_old.csv` from the bundle — it has a
  completely different, tiny schema (5 columns, 20 rows) left over from an
  early version of the project and isn't referenced anywhere in the code.

## UI / style upgrade (app.py)
- Added the Inter font and a subtle fade-in animation for the page.
- Hero banner now has a slow animated gradient instead of a static one.
- Product cards lift up with a soft shadow on hover.
- Added a proper discount badge on the product image corner (removed the
  redundant discount text that was duplicated in the rating row).
- Restyled the native Streamlit widgets (search box, buttons, dropdowns,
  tabs, expander) so they match the rest of the design instead of looking
  like default Streamlit components.

## How to run
1. `pip install -r requirements.txt`
2. `streamlit run app.py`

## Fix: raw HTML tags showing up as literal text
The hero banner, stat cards, product cards, and footer used st.markdown(html,
unsafe_allow_html=True) with indented, multi-line HTML strings that had
blank lines in them. Markdown's HTML-block rule stops treating a block as
raw HTML once it hits a blank line, and indented lines after that point get
read as a literal code block instead - which is why some <div> tags were
rendering as visible text instead of styled elements.

Fixed by adding a small render_html() helper that strips indentation and
blank lines from the HTML string before handing it to st.markdown(), so
Markdown can no longer misinterpret any part of it as code. All raw-HTML
blocks now go through this helper.

## New: type price hints straight into the search box
The search box now understands phrases like:
- "shoes under 3000" / "earbuds below 2k" / "laptop upto 15000"
- "phone above 50000" / "tv over 40k" / "watch more than 10000"
- "headphones between 1000 and 3000"

It strips the price phrase out before doing the text search (so it does not
confuse the TF-IDF matching) and turns it into an actual min/max price
filter. This combines with the sidebar Max Price slider and Minimum
Rating - whichever constraint is tighter wins, so the sidebar keeps working
exactly as before rather than being overridden by the search box.

## Fixed: nonsensical brand/category pairs (e.g. "LG" under "Fashion")
The original data.csv had brand and category assigned completely at
random - every one of the 15 brands showed up in every one of the 8
categories in roughly equal numbers, which is why things like "LG" or
"Nike" would show up as toy or beauty brands.

data.csv has been rewritten so every product's brand actually fits its
category:
- Electronics: Apple, Boat, Dell, HP, LG, Philips, Redmi, Samsung, Sony
- Mobiles: Apple, Redmi, Samsung
- Appliances / Home & Kitchen: LG, Philips, Prestige, Samsung, Whirlpool
- Fashion / Sports: Adidas, Nike, Puma, Reebok
- Beauty: Philips, Lakme, Mamaearth
- Toys: Funskool, Lego, Hamleys

(Lakme, Mamaearth, Funskool, Lego, and Hamleys were added because none of
the original 15 brands are genuine toy or beauty brands - without adding
a few realistic names, those two categories would have had no valid brand
at all.)

Only the `brand` and `product_name` columns were changed (product_name's
brand prefix was regenerated to match), all 80,000 rows and every other
column (price, rating, stock, etc.) are untouched. Category and brand
dropdowns will now always show a consistent, realistic combination.

## Simplified to a Flipkart-style layout
- Removed the search bar entirely - the sidebar (Category, Brand,
  Minimum Rating, Maximum Price) is now the only way to narrow results.
- Removed "Products to Display" from the sidebar - it's fixed at 12.
- Product cards now show only what a real storefront shows: Category,
  Product name, Price, and Rating. Removed the discount badge, the
  crossed-out old price, and the "AI Score" badge.
- Recolored the whole app from purple/violet to Flipkart's blue
  (#2874f0) and orange (#fb641b) palette.

## Fixed: dropdown text invisible (white text on white background)
The sidebar's dark background was styled by forcing every bit of text
inside it to white (`section[data-testid="stSidebar"] * { color: white
!important; }`). That rule also caught the dropdown's own white
background box, so the selected Category/Brand text was rendered white
on white and effectively invisible.

Fixed with two changes:
1. A `.streamlit/config.toml` now pins the app to a light theme with
   Flipkart's blue as the primary color, so the app looks the same
   regardless of whether the user's browser/OS is in dark mode (dark
   mode was very likely why this only showed up for some people and not
   others).
2. Added a specific override so the dropdown's own text and background
   always stay dark-on-white, and the same for the options list that
   appears when a dropdown is opened, which renders separately and
   needed its own fix.
