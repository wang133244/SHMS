from app.core.config import get_settings


def embed_text(text: str) -> list[float] | None:
    settings = get_settings()
    if not settings.llm_api_key:
        return None
    from langchain_openai import OpenAIEmbeddings

    embeddings = OpenAIEmbeddings(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url or None,
        model="text-embedding-3-small",
    )
    return embeddings.embed_query(text)
