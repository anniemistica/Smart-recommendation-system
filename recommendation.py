import pandas as pd
import numpy as np
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


DATA_FILE = "data.csv"


def load_data():
    """
    Load and clean the Flipkart retail dataset.
    """

    df = pd.read_csv(DATA_FILE)

    # Remove completely duplicated rows
    df = df.drop_duplicates()

    # Convert numeric columns safely
    numeric_columns = [
        "price",
        "discount_percent",
        "final_price",
        "rating",
        "review_count",
        "stock_available",
        "units_sold",
        "delivery_days",
        "weight_g",
        "warranty_months",
        "return_policy_days",
        "shipping_weight_g",
        "product_score",
        "seller_rating"
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    # Fill numeric missing values with median
    for column in numeric_columns:
        if column in df.columns:
            df[column] = df[column].fillna(
                df[column].median()
            )

    # Text columns
    text_columns = [
        "product_name",
        "category",
        "brand",
        "seller",
        "seller_city",
        "color",
        "size",
        "return_policy",
        "payment_modes"
    ]

    for column in text_columns:
        if column in df.columns:
            df[column] = df[column].fillna("Unknown").astype(str)

    return df


def normalize_series(series):
    """
    Min-max normalization.
    """

    minimum = series.min()
    maximum = series.max()

    if maximum == minimum:
        return pd.Series(
            np.ones(len(series)),
            index=series.index
        )

    return (series - minimum) / (maximum - minimum)


def clean_text(text):
    """
    Clean search text.
    """

    text = str(text).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def _parse_price_number(number_text, k_suffix):
    """
    Turn '3,000' / '3000' / '3k' style price text into a float.
    """

    value = float(number_text.replace(",", ""))

    if k_suffix:
        value *= 1000

    return value


def extract_price_constraints(query):
    """
    Look for natural-language price hints typed directly into the search
    box - e.g. "wireless earbuds under 2000", "laptop above 50000",
    "shoes between 1000 and 3000", "phone below 15k" - and pull them out
    as an explicit min/max price.

    Returns (cleaned_query, min_price, max_price):
    - cleaned_query has the price phrase removed, so it doesn't confuse
      the TF-IDF text search with numbers/keywords that aren't actually
      part of the product description.
    - min_price / max_price are None when no such hint was found.
    """

    text = str(query).lower()

    number = r"(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d+)?)\s*(k)?"

    min_price = None
    max_price = None

    # "between 1000 and 5000" / "1000 to 5000" / "1000-5000"
    between_pattern = (
        r"\bbetween\s*" + number +
        r"\s*(?:and|to|-)\s*" + number + r"\b"
    )

    match = re.search(between_pattern, text)

    if match:
        min_price = _parse_price_number(match.group(1), match.group(2))
        max_price = _parse_price_number(match.group(3), match.group(4))
        text = text[:match.start()] + " " + text[match.end():]

    else:
        # "under 3000" / "below 3000" / "less than 3000" / "upto 3000"
        max_pattern = (
            r"\b(?:under|below|less\s*than|up\s*to|upto|max(?:imum)?)\s*"
            + number + r"\b"
        )

        match = re.search(max_pattern, text)

        if match:
            max_price = _parse_price_number(match.group(1), match.group(2))
            text = text[:match.start()] + " " + text[match.end():]

        # "above 50000" / "over 50000" / "more than 50000" / "min 50000"
        min_pattern = (
            r"\b(?:above|over|more\s*than|greater\s*than|min(?:imum)?)\s*"
            + number + r"\b"
        )

        match = re.search(min_pattern, text)

        if match:
            min_price = _parse_price_number(match.group(1), match.group(2))
            text = text[:match.start()] + " " + text[match.end():]

    text = re.sub(r"\s+", " ", text).strip()

    return text, min_price, max_price


def create_search_text(df):
    """
    Combine important product information
    into a searchable text representation.
    """

    return (
        df["product_name"].astype(str) + " " +
        df["category"].astype(str) + " " +
        df["brand"].astype(str) + " " +
        df["seller"].astype(str) + " " +
        df["color"].astype(str) + " " +
        df["size"].astype(str)
    ).apply(clean_text)


def search_products(
    query="",
    category="All",
    brand="All",
    min_rating=0.0,
    max_price=None,
    number_of_products=12,
    df=None
):
    """
    Hybrid product search and recommendation system.

    Combines:
    1. TF-IDF text relevance
    2. Rating
    3. Review popularity
    4. Discount
    5. Product score
    6. Seller rating
    7. Units sold
    8. Stock availability
    9. Price suitability
    10. Delivery performance

    A pre-loaded/cached dataframe can be passed in via `df` to avoid
    re-reading and re-cleaning the CSV file on every single search
    (this was previously happening on every interaction, which is
    very slow on a large dataset).
    """

    if df is None:
        df = load_data()

    # --------------------------------------------------
    # PRICE HINTS TYPED INTO THE SEARCH BOX
    # --------------------------------------------------
    # e.g. "shoes under 3000" or "laptop above 50000". These are combined
    # with (not a replacement for) the sidebar's min-rating/max-price
    # filters below - whichever constraint is more restrictive wins.

    query, query_min_price, query_max_price = extract_price_constraints(
        query
    )

    effective_max_price = max_price

    if query_max_price is not None:
        effective_max_price = (
            query_max_price
            if effective_max_price is None
            else min(effective_max_price, query_max_price)
        )

    effective_min_price = query_min_price

    # --------------------------------------------------
    # BASIC FILTERING
    # --------------------------------------------------

    filtered = df.copy()

    if category != "All":
        filtered = filtered[
            filtered["category"].str.lower()
            == category.lower()
        ]

    if brand != "All":
        filtered = filtered[
            filtered["brand"].str.lower()
            == brand.lower()
        ]

    filtered = filtered[
        filtered["rating"] >= min_rating
    ]

    if effective_max_price is not None:
        filtered = filtered[
            filtered["final_price"] <= effective_max_price
        ]

    if effective_min_price is not None:
        filtered = filtered[
            filtered["final_price"] >= effective_min_price
        ]

    if filtered.empty:
        return pd.DataFrame()

    # --------------------------------------------------
    # NORMALIZED ML FEATURES
    # --------------------------------------------------

    filtered["rating_score"] = (
        filtered["rating"] / 5
    )

    filtered["review_score"] = normalize_series(
        np.log1p(filtered["review_count"])
    )

    filtered["discount_score"] = (
        filtered["discount_percent"].clip(0, 100) / 100
    )

    filtered["product_score_normalized"] = (
        normalize_series(
            filtered["product_score"]
        )
    )

    filtered["seller_score"] = (
        filtered["seller_rating"] / 5
    )

    filtered["sales_score"] = normalize_series(
        np.log1p(filtered["units_sold"])
    )

    filtered["stock_score"] = (
        filtered["stock_available"] > 0
    ).astype(float)

    # Higher score for faster delivery
    delivery_inverse = (
        filtered["delivery_days"].max()
        - filtered["delivery_days"]
    )

    filtered["delivery_score"] = normalize_series(
        delivery_inverse
    )

    # --------------------------------------------------
    # TF-IDF SEARCH MODEL
    # --------------------------------------------------

    search_text = create_search_text(filtered)

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1
    )

    tfidf_matrix = vectorizer.fit_transform(
        search_text
    )

    query = clean_text(query)

    if query:
        query_vector = vectorizer.transform(
            [query]
        )

        text_similarity = cosine_similarity(
            query_vector,
            tfidf_matrix
        ).flatten()

    else:
        # If no search query is supplied,
        # give every product equal text relevance.
        text_similarity = np.ones(
            len(filtered)
        )

    filtered["text_relevance"] = text_similarity

    # --------------------------------------------------
    # PRICE SCORE
    # --------------------------------------------------

    if effective_max_price is not None:

        price_difference = abs(
            effective_max_price - filtered["final_price"]
        )

        filtered["price_score"] = 1 - (
            price_difference /
            max(effective_max_price, 1)
        )

        filtered["price_score"] = (
            filtered["price_score"]
            .clip(0, 1)
        )

    else:

        filtered["price_score"] = 0.5

    # --------------------------------------------------
    # HYBRID RECOMMENDATION SCORE
    # --------------------------------------------------

    filtered["recommendation_score"] = (

        # Search relevance
        filtered["text_relevance"] * 0.30

        # Product quality
        + filtered["rating_score"] * 0.16

        # Customer popularity
        + filtered["review_score"] * 0.10

        # Discount attractiveness
        + filtered["discount_score"] * 0.08

        # Product score
        + filtered["product_score_normalized"] * 0.10

        # Seller quality
        + filtered["seller_score"] * 0.08

        # Sales popularity
        + filtered["sales_score"] * 0.07

        # Stock availability
        + filtered["stock_score"] * 0.04

        # Delivery performance
        + filtered["delivery_score"] * 0.04

        # Price suitability
        + filtered["price_score"] * 0.03
    )

    # --------------------------------------------------
    # SORT RESULTS
    # --------------------------------------------------

    filtered = filtered.sort_values(
        by="recommendation_score",
        ascending=False
    )

    # --------------------------------------------------
    # RETURN EXACT REQUESTED NUMBER
    # --------------------------------------------------

    return filtered.head(
        number_of_products
    ).reset_index(drop=True)


def get_categories():
    """
    Return all product categories.
    """

    df = load_data()

    return sorted(
        df["category"]
        .dropna()
        .unique()
        .tolist()
    )


def get_brands(category="All", df=None, top_n=100):
    """
    Return popular brands, optionally narrowed to a single category.

    Pass `category="All"` (default) for the top brands across the whole
    catalog, or a specific category name to only get brands that actually
    have products listed in that category.
    """

    if df is None:
        df = load_data()

    if category != "All":
        df = df[
            df["category"].str.lower() == category.lower()
        ]

    brands = (
        df["brand"]
        .value_counts()
        .head(top_n)
        .index
        .tolist()
    )

    return sorted(brands)


def get_product_statistics():
    """
    Return useful dataset statistics.
    """

    df = load_data()

    return {
        "total_products": len(df),
        "total_categories": df["category"].nunique(),
        "total_brands": df["brand"].nunique(),
        "average_rating": round(
            df["rating"].mean(),
            2
        ),
        "average_price": round(
            df["final_price"].mean(),
            2
        ),
        "average_discount": round(
            df["discount_percent"].mean(),
            2
        )
    }


def get_similar_products(
    product_name,
    number_of_products=8,
    df=None
):
    """
    Find products similar to a selected product
    using TF-IDF similarity.

    A pre-loaded/cached dataframe can be passed in via `df` to avoid
    re-reading and re-cleaning the CSV file every time a similarity
    lookup is requested.
    """

    if df is None:
        df = load_data()
    else:
        df = df.copy()

    if df.empty:
        return pd.DataFrame()

    search_text = create_search_text(df)

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2)
    )

    matrix = vectorizer.fit_transform(
        search_text
    )

    product_matches = df[
        df["product_name"].astype(str).str.lower()
        == str(product_name).lower()
    ]

    if product_matches.empty:
        return pd.DataFrame()

    product_index = product_matches.index[0]

    position = df.index.get_loc(
        product_index
    )

    similarity_scores = cosine_similarity(
        matrix[position],
        matrix
    ).flatten()

    df["similarity_score"] = similarity_scores

    # Remove the selected product itself
    df = df.drop(
        index=product_index
    )

    recommendations = df.sort_values(
        by="similarity_score",
        ascending=False
    )

    return recommendations.head(
        number_of_products
    ).reset_index(drop=True)