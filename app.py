
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from recommendation import (
    load_data,
    search_products,
    get_categories,
    get_brands,
    get_product_statistics,
    get_similar_products
)


def render_html(html):
    """
    Render a raw HTML string in Streamlit.

    A plain st.markdown(html, unsafe_allow_html=True) call can misfire when
    the HTML string has indentation and/or blank lines in it (which is
    normal when it's written as an indented triple-quoted string in Python).
    Markdown's HTML-block rule only recognizes a tag as raw HTML if the line
    is not indented 4+ spaces, and a blank line inside the block ends it,
    so any indented lines *after* that blank line get treated as a literal
    code block instead of HTML - which is exactly the "raw tags showing up
    as text" bug. Stripping every line's leading/trailing whitespace and
    joining them back together removes any indentation for Markdown to
    misinterpret, so the whole block always renders as real HTML.
    """

    lines = [line.strip() for line in html.strip().splitlines()]
    lines = [line for line in lines if line]  # drop blank lines entirely
    cleaned = " ".join(lines)
    st.markdown(cleaned, unsafe_allow_html=True)


# ============================================================
# PAGE CONFIGURATION
# ===========================================================

st.set_page_config(
    page_title="SmartCart AI",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background: radial-gradient(
            circle at top left,
            #f5f3ff 0%,
            #f8fafc 35%,
            #f8fafc 100%
        );
    }

    /* Smooth fade-in for the whole app */
    .main .block-container {
        animation: fadeIn 0.5s ease-in-out;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .main .block-container {
        max-width: 1450px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    section[data-testid="stSidebar"] {
        background-color: #172554;
    }

    section[data-testid="stSidebar"] * {
        color: pink !important;
    }

    /* The rule above turns every bit of sidebar text white, which also
       hits the dropdown's own white background box and makes the
       selected value unreadable (white text on white). These widgets
       need their own dark text back, since their background stays
       white by design (matching a real e-commerce site look). */
    section[data-testid="stSidebar"] div[data-baseweb="select"] *,
    section[data-testid="stSidebar"] div[data-baseweb="select"] input {
        color: #212121 !important;
    }

    div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        border: 1px solid #d1d5db !important;
        border-radius: 4px !important;
    }

    /* The options list that drops down when a selectbox is opened
       renders in its own floating layer, so it needs the same
       white-background / dark-text treatment explicitly. */
    div[data-baseweb="popover"] li,
    ul[role="listbox"] li {
        background-color: #ffffff !important;
        color: #212121 !important;
    }

    div[data-baseweb="popover"] li:hover,
    ul[role="listbox"] li:hover {
        background-color: #e8f0fe !important;
    }

    .hero-box {
        background: linear-gradient(
            120deg,
            #172554 0%,
            #1d4ed8 45%,
            #2874f0 90%,
            #38bdf8 130%
        );
        background-size: 200% 200%;
        animation: heroShift 10s ease-in-out infinite;

        padding: 42px;
        border-radius: 28px;
        margin-bottom: 30px;

        box-shadow: 0 20px 50px rgba(29, 78, 216, 0.25);
    }

    @keyframes heroShift {
        0%   { background-position: 0% 50%; }
        50%  { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    .hero-title {
        color: white;
        font-size: 3rem;
        font-weight: 800;
        margin-bottom: 10px;
    }

    .hero-description {
        color: white;
        opacity: 0.9;
        font-size: 1.1rem;
        line-height: 1.7;
    }

    .hero-badge {
        color: white;
        background: rgba(255,255,255,0.15);
        border-radius: 50px;
        padding: 8px 15px;
        display: inline-block;
        margin-bottom: 15px;
        font-size: 0.85rem;
    }

    .ai-box {
        background: #eaf1ff;
        border: 1px solid #bfd7ff;
        border-radius: 18px;
        padding: 20px;
        margin-top: 20px;
        margin-bottom: 25px;
    }

    .ai-title {
        color: #1d4ed8;
        font-size: 1.1rem;
        font-weight: 800;
        margin-bottom: 8px;
    }

    .ai-description {
        color: #1e3a8a;
        line-height: 1.6;
    }

    .product-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 20px;
        padding: 18px;
        margin-bottom: 20px;
        min-height: 390px;
        box-shadow: 0 8px 25px rgba(15,23,42,0.06);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        position: relative;
    }

    .product-card:hover {
        transform: translateY(-6px);
        box-shadow: 0 18px 35px rgba(76, 29, 149, 0.15);
        border-color: #c7d2fe;
    }

    .product-image {
        height: 140px;
        border-radius: 16px;
        background: linear-gradient(
            135deg,
            #eef2ff,
            #fdf2f8
        );

        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;

        font-size: 4rem;
        margin-bottom: 15px;
    }

    .product-category {
        color: #2874f0;
        font-size: 0.75rem;
        font-weight: 800;
        text-transform: uppercase;
        margin-bottom: 7px;
    }

    .product-name {
        color: #111827;
        font-size: 1rem;
        font-weight: 750;
        min-height: 48px;
    }

    .product-price {
        color: #111827;
        font-size: 1.35rem;
        font-weight: 800;
    }

    .product-rating {
        display: inline-block;
        background: #388e3c;
        color: white;
        font-size: 0.8rem;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 6px;
        margin-top: 10px;
    }

    .stat-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 8px 25px rgba(15,23,42,0.05);
    }

    .stat-icon {
        font-size: 1.8rem;
    }

    .stat-value {
        color: #111827;
        font-size: 1.7rem;
        font-weight: 800;
    }

    .stat-label {
        color: #64748b;
        font-size: 0.85rem;
    }

    .footer {
        margin-top: 60px;
        padding: 25px;
        text-align: center;
        color: #64748b;
        border-top: 1px solid #e2e8f0;
    }

    /* ---------- Native widget styling ---------- */

    .stButton > button {
        background: #fb641b;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 10px 22px;
        font-weight: 700;
        box-shadow: 0 8px 18px rgba(251, 100, 27, 0.28);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }

    .stButton > button:hover {        
        color: black;
    }

    section[data-testid="stSidebar"] .stSlider {
        padding-top: 4px;
    }

    button[data-baseweb="tab"] {
        font-weight: 700;
        border-radius: 10px 10px 0 0;
    }

    div[data-testid="stExpander"] {
        border-radius: 16px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 4px 14px rgba(15,23,42,0.04);
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data
def get_dataset():
    return load_data()


df = get_dataset()


# ============================================================
# CACHE FILTER DATA
# ============================================================

@st.cache_data
def get_category_list():
    return ["All"] + get_categories()


@st.cache_data
def get_statistics():
    return get_product_statistics()


categories = get_category_list()
stats = get_statistics()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🛍️ Smart Product Recommendation System")

st.sidebar.caption(
    "Intelligent Product Discovery"
)

st.sidebar.divider()

st.sidebar.subheader(
    "🎯 Refine Your Search"
)


selected_category = st.sidebar.selectbox(
    "Category",
    categories
)


# The brand list depends on the category chosen above, so it's computed
# fresh each rerun (fast: it's just a value_counts on an already-loaded
# dataframe) instead of being one static list for the whole catalog.
brands = ["All"] + get_brands(
    category=selected_category,
    df=df
)

selected_brand = st.sidebar.selectbox(
    "Brand",
    brands
)


minimum_rating = st.sidebar.slider(
    "Minimum Rating",
    min_value=0.0,
    max_value=5.0,
    value=0.0,
    step=0.1
)


data_max_price = int(
    df["final_price"].max()
)


selected_max_price = st.sidebar.slider(
    "Maximum Price (₹)",
    min_value=100,
    max_value=max(data_max_price, 100),
    value=min(50000, max(data_max_price, 100)),
    step=500
)


number_of_products = 12


st.sidebar.divider()

st.sidebar.info(
    "💡 Tip\n\n"
    "Narrow things down using Category, Brand, "
    "Minimum Rating, and Maximum Price."
)



# ============================================================
# HERO
# ============================================================

render_html(
    """
    <div class="hero-box">
        <div class="hero-badge">
            🤖 AI-POWERED PRODUCT DISCOVERY
        </div>

        <div class="hero-title">
            Smart Product Recommendation System🛒📈💰📊
        </div>

        <div class="hero-description">
            Discover better products using intelligent search,
            machine-learning based ranking and personalized
            recommendations from a large retail dataset.
        </div>
    </div>
    """
)


# ============================================================
# PRODUCT RESULTS
# ============================================================

with st.spinner(
    "Loading products..."
):

    results = search_products(
        query="",
        category=selected_category,
        brand=selected_brand,
        min_rating=minimum_rating,
        max_price=selected_max_price,
        number_of_products=number_of_products,
        df=df
    )


# ============================================================
# AI EXPLANATION
# ============================================================

render_html(
    """
    <div class="ai-box">

        <div class="ai-title">
            🤖 How It ranks products . . .
        </div>

        <div class="ai-description">
            Products are ranked using a hybrid machine-learning
            methodology combining search relevance, product rating,
            customer reviews, discount, product score, seller rating,
            popularity, stock availability, delivery performance
            and price suitability.
        </div>

    </div>
    """
)


# ============================================================
# RECOMMENDED PRODUCTS
# ============================================================

st.header("✨ Recommended Products")


if not results.empty:

    st.caption(
        f"Showing {len(results)} intelligently ranked products"
    )

    for start in range(
        0,
        len(results),
        4
    ):

        row = results.iloc[
            start:start + 4
        ]

        columns = st.columns(4)

        for column, (_, product) in zip(
            columns,
            row.iterrows()
        ):

            with column:

                product_name = str(
                    product["product_name"]
                )

                category = str(
                    product["category"]
                )

                price = float(
                    product["final_price"]
                )

                rating = float(
                    product["rating"]
                )


                category_lower = category.lower()


                if (
                    "electronic" in category_lower
                    or "mobile" in category_lower
                    or "computer" in category_lower
                ):
                    emoji = "💻"

                elif "fashion" in category_lower:
                    emoji = "👕"

                elif "beauty" in category_lower:
                    emoji = "💅"

                elif "home" in category_lower:
                    emoji = "💾 "

                elif "sport" in category_lower:
                    emoji = "🏏"

                elif "book" in category_lower:
                    emoji = "📚"

                elif "grocery" in category_lower:
                    emoji = "🛒"

                elif "appliance" in category_lower:
                    emoji = "🔌"

                else:
                    emoji = "🧸"


                # Product image area

                render_html(
                    f"""
                    <div class="product-card">

                        <div class="product-image">
                            {emoji}
                        </div>

                        <div class="product-category">
                            {category}
                        </div>

                        <div class="product-name">
                            {product_name}
                        </div>

                        <div style="margin-top:12px;">
                            <span class="product-price">
                                ₹{price:,.0f}
                            </span>
                        </div>

                        <div class="product-rating">
                            ⭐ {rating:.1f}
                        </div>

                    </div>
                    """
                )


else:

    st.warning(
        "No products match your current filters. "
        "Try increasing the price limit or lowering "
        "the minimum rating."
    )


# ============================================================
# DATASET STATISTICS
# ============================================================

st.header("📊 Dataset Intelligence")

st.caption(
    "Overview of the retail dataset"
)


stat_columns = st.columns(5)


stat_data = [

    (
        "📦",
        f"{stats['total_products']:,}",
        "Total Products"
    ),

    (
        "🗂️",
        f"{stats['total_categories']:,}",
        "Categories"
    ),

    (
        "🏷️",
        f"{stats['total_brands']:,}",
        "Brands"
    ),

    (
        "⭐",
        f"{stats['average_rating']:.2f}",
        "Average Rating"
    ),

    (
        "💰",
        f"₹{stats['average_price']:,.0f}",
        "Average Price"
    )

]


for column, data in zip(
    stat_columns,
    stat_data
):

    icon, value, label = data

    with column:

        render_html(
            f"""
            <div class="stat-card">

                <div class="stat-icon">
                    {icon}
                </div>

                <div class="stat-value">
                    {value}
                </div>

                <div class="stat-label">
                    {label}
                </div>

            </div>
            """
        )


# ============================================================
# SIMILAR PRODUCT FINDER
# ============================================================

st.header("🔗 Similar Product Finder")

st.caption(
    "Select a product to discover similar products "
    "using TF-IDF content similarity."
)


sample_products = (
    df["product_name"]
    .dropna()
    .astype(str)
    .drop_duplicates()
    .head(500)
    .tolist()
)


if sample_products:

    selected_product = st.selectbox(
        "Choose a product",
        sample_products
    )


    if st.button(
        "🔗 Find Similar Products",
        use_container_width=False
    ):

        with st.spinner(
            "🔍 Finding similar products..."
        ):

            similar = get_similar_products(
                selected_product,
                number_of_products=8,
                df=df
            )


        if not similar.empty:

            st.success(
                f"Found {len(similar)} similar products."
            )


            similar_display = similar[
                [
                    "product_name",
                    "category",
                    "final_price",
                    "rating",
                    "similarity_score"
                ]
            ].copy()


            similar_display.columns = [
                "Product",
                "Category",
                "Price",
                "Rating",
                "Similarity"
            ]


            similar_display["Price"] = (
                similar_display["Price"]
                .apply(
                    lambda x: f"₹{x:,.0f}"
                )
            )


            similar_display["Rating"] = (
                similar_display["Rating"]
                .apply(
                    lambda x: f"⭐ {x:.1f}"
                )
            )


            similar_display["Similarity"] = (
                similar_display["Similarity"]
                .apply(
                    lambda x: f"{x:.2f}"
                )
            )


            st.dataframe(
                similar_display,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                "No similar products were found."
            )


# ============================================================
# EXPLORATORY DATA ANALYSIS
# ============================================================

st.header("📈 Exploratory Data Analysis")

st.caption(
    "Visual analysis of the retail dataset."
)


eda_tab1, eda_tab2, eda_tab3 = st.tabs(
    [
        "⭐ Ratings",
        "💰 Prices",
        "🏷️ Categories"
    ]
)


# ============================================================
# RATINGS
# ============================================================

with eda_tab1:

    rating_distribution = (
        df["rating"]
        .round(1)
        .value_counts()
        .sort_index()
    )


    fig1, ax1 = plt.subplots(
        figsize=(10, 4)
    )


    ax1.bar(
        rating_distribution.index.astype(str),
        rating_distribution.values
    )


    ax1.set_title(
        "Product Rating Distribution"
    )

    ax1.set_xlabel(
        "Rating"
    )

    ax1.set_ylabel(
        "Number of Products"
    )


    plt.xticks(
        rotation=45
    )


    st.pyplot(
        fig1,
        use_container_width=True
    )


    plt.close(fig1)


# ============================================================
# PRICES
# ============================================================

with eda_tab2:

    fig2, ax2 = plt.subplots(
        figsize=(10, 4)
    )


    ax2.hist(
        df["final_price"],
        bins=40
    )


    ax2.set_title(
        "Product Price Distribution"
    )

    ax2.set_xlabel(
        "Final Price (₹)"
    )

    ax2.set_ylabel(
        "Number of Products"
    )


    st.pyplot(
        fig2,
        use_container_width=True
    )


    plt.close(fig2)


# ============================================================
# CATEGORIES
# ============================================================

with eda_tab3:

    category_counts = (
        df["category"]
        .value_counts()
        .head(15)
    )


    fig3, ax3 = plt.subplots(
        figsize=(10, 5)
    )


    ax3.barh(
        category_counts.index,
        category_counts.values
    )


    ax3.set_title(
        "Top Product Categories"
    )

    ax3.set_xlabel(
        "Number of Products"
    )


    ax3.invert_yaxis()


    st.pyplot(
        fig3,
        use_container_width=True
    )


    plt.close(fig3)


# ============================================================
# DATASET PREVIEW
# ============================================================

st.header("📋 Explore Raw Dataset")


with st.expander(
    "Open Dataset Preview"
):

    st.dataframe(
        df.head(100),
        use_container_width=True
    )


# ============================================================
# FOOTER
# ============================================================

render_html(
    """
    <div class="footer">

        <strong>🛍️ Product recommendation System !!</strong>

        <br><br>

        Hybrid Machine Learning Product Recommendation System

        <br>

        Built with Python • Pandas • NumPy • Scikit-learn • Streamlit

    </div>
    """
)
