import pandas as pd

# Creating standard example rows using a scraping sandbox (books.toscrape.com)
# This provides stable testing and avoids external rate limits / blocking during validation.
data = [
    {
        "Metal": "Gold",
        "City": "New York",
        "URL": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        "Selector": ".price_color"
    },
    {
        "Metal": "Silver",
        "City": "London",
        "URL": "https://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html",
        "Selector": ".price_color"
    },
    {
        "Metal": "Gold",
        "City": "Tokyo",
        "URL": "https://books.toscrape.com/catalogue/soumission_998/index.html",
        "Selector": None  # Will trigger the regex numeric fallback
    }
]

df = pd.DataFrame(data)
df.to_excel("urls.xlsx", index=False)
print("Successfully generated urls.xlsx")
