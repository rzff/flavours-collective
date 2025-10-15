import os
import asyncio
import json
from pydantic import BaseModel, Field
from typing import List
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode,
    LLMConfig,
)
from crawl4ai import LLMExtractionStrategy


class Product(BaseModel):
    name: str
    price: str
    link: str
    images: List[str]


async def main():
    # 1. Define the LLM extraction strategy
    llm_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(provider="ollama/deepseek-r1:8b", api_token="none"),
        schema=Product.schema_json(),  # Or use model_json_schema()
        extraction_type="schema",
        instruction="Extract all products with name, price, link (which is the redirection link) and all images. First check the total amount of products, then ",
        chunk_token_threshold=1000,
        overlap_rate=0.0,
        apply_chunking=True,
        input_format="html",  # or "html", "fit_markdown"
        extra_args={"temperature": 0.0, "max_tokens": 800},
    )

    # 2. Build the crawler config
    crawl_config = CrawlerRunConfig(
        extraction_strategy=llm_strategy,
        cache_mode=CacheMode.DISABLED,
        remove_overlay_elements=True,
        magic=True,
        simulate_user=True,
        override_navigator=True,
        check_robots_txt=True,
    )

    # 3. Create a browser config if needed
    browser_cfg = BrowserConfig(headless=False)

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        # 4. Let's say we want to crawl a single page
        print("starting crawling with update")
        result = await crawler.arun(
            url="https://www.aimeleondore.com/collections/shop-all", config=crawl_config
        )
        print("ended crawling")

        if result.success:
            # 5. The extracted content is presumably JSON
            data = json.loads(result.extracted_content)
            print("Extracted items:", data)

            # 6. Show usage stats
            llm_strategy.show_usage()  # prints token usage
        else:
            print("Error:", result.error_message)


if __name__ == "__main__":
    asyncio.run(main())
