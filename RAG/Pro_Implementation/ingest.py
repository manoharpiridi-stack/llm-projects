import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field
from chromadb import PersistentClient
from tqdm import tqdm
from openai import OpenAI
from tenacity import retry, wait_exponential

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT.parent / ".env")
load_dotenv(ROOT / ".env")

DB_NAME = str(ROOT / "preprocessed_db")
COLLECTION_NAME = "docs"
KNOWLEDGE_BASE_PATH = ROOT / "knowledge-base"
AVERAGE_CHUNK_SIZE = 250
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHAT_MODEL = os.getenv("RAG_INGEST_MODEL", "openai/gpt-oss-20b")
USE_LLM_CHUNKING = os.getenv("RAG_LLM_CHUNK", "").strip().lower() in {"1", "true", "yes"}

wait = wait_exponential(multiplier=1, min=2, max=30)

_embeddings = None
_chroma = None


def groq_client():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY is missing from the .env file.")
    return OpenAI(api_key=key.strip(), base_url="https://api.groq.com/openai/v1")


def get_local_embeddings():
    global _embeddings
    if _embeddings is None:
        from langchain_huggingface import HuggingFaceEmbeddings

        _embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings


def embed_texts(texts: list[str]) -> list[list[float]]:
    return get_local_embeddings().embed_documents(texts)


def embed_query(text: str) -> list[float]:
    return get_local_embeddings().embed_query(text)


def chroma_client():
    global _chroma
    if _chroma is None:
        _chroma = PersistentClient(path=DB_NAME)
    return _chroma


def collection_names():
    names = []
    for item in chroma_client().list_collections():
        names.append(item.name if hasattr(item, "name") else str(item))
    return names


def get_collection():
    return chroma_client().get_or_create_collection(COLLECTION_NAME)


def collection_ready():
    try:
        return COLLECTION_NAME in collection_names() and get_collection().count() > 0
    except Exception:
        return False


class Result(BaseModel):
    page_content: str
    metadata: dict


class Chunk(BaseModel):
    headline: str = Field(
        description="A brief heading for this chunk, typically a few words, that is most likely to be surfaced in a query",
    )
    summary: str = Field(
        description="A few sentences summarizing the content of this chunk to answer common questions"
    )
    original_text: str = Field(
        description="The original text of this chunk from the provided document, exactly as is, not changed in any way"
    )

    def as_result(self, document):
        metadata = {"source": document["source"], "type": document["type"]}
        return Result(
            page_content=self.headline + "\n\n" + self.summary + "\n\n" + self.original_text,
            metadata=metadata,
        )


class Chunks(BaseModel):
    chunks: list[Chunk]


def fetch_documents():
    documents = []
    for folder in KNOWLEDGE_BASE_PATH.iterdir():
        if not folder.is_dir():
            continue
        doc_type = folder.name
        for file in folder.rglob("*.md"):
            with open(file, "r", encoding="utf-8") as handle:
                documents.append(
                    {"type": doc_type, "source": file.as_posix(), "text": handle.read()}
                )
    print(f"Loaded {len(documents)} documents")
    return documents


def make_prompt(document):
    how_many = (len(document["text"]) // AVERAGE_CHUNK_SIZE) + 1
    return f"""
You take a document and you split the document into overlapping chunks for a KnowledgeBase.

The document is from the shared drive of a company called Insurellm.
The document is of type: {document["type"]}
The document has been retrieved from: {document["source"]}

A chatbot will use these chunks to answer questions about the company.
Divide up the document so the entire document is returned across the chunks.
This document should probably be split into at least {how_many} chunks, with about 25% overlap.

For each chunk, provide a headline, a summary, and the original text of the chunk.

Here is the document:

{document["text"]}

Respond with JSON: {{"chunks": [{{"headline": "...", "summary": "...", "original_text": "..."}}]}}
"""


def first_heading(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or fallback
    return fallback


def short_summary(text: str, limit: int = 280) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    trimmed = cleaned[: limit - 1].rsplit(" ", 1)[0]
    return trimmed + "…"


def chunk_document_locally(document) -> list[Result]:
    title = Path(document["source"]).stem
    heading = first_heading(document["text"], title)
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=200)
    pieces = splitter.split_text(document["text"])
    if not pieces:
        pieces = [document["text"]]
    results = []
    for piece in pieces:
        chunk = Chunk(
            headline=f"{document['type']}: {heading}",
            summary=short_summary(piece),
            original_text=piece,
        )
        results.append(chunk.as_result(document))
    return results


def parse_chunks(raw: str, document) -> list[Result]:
    text = (raw or "").strip()
    try:
        parsed = Chunks.model_validate_json(text)
        return [chunk.as_result(document) for chunk in parsed.chunks]
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            parsed = Chunks.model_validate_json(text[start : end + 1])
            return [chunk.as_result(document) for chunk in parsed.chunks]
        return [
            Result(
                page_content=document["text"],
                metadata={"source": document["source"], "type": document["type"]},
            )
        ]


@retry(wait=wait)
def process_document(document):
    client = groq_client()
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": make_prompt(document)}],
        response_format={"type": "json_object"},
    )
    return parse_chunks(response.choices[0].message.content or "", document)


def create_chunks(documents):
    chunks = []
    if USE_LLM_CHUNKING:
        print("LLM chunking is on (RAG_LLM_CHUNK=1). This calls Groq once per file and is slow.")
        for document in tqdm(documents, desc="LLM chunking"):
            chunks.extend(process_document(document))
        return chunks

    print("Local chunking with headline + summary (no Groq). Query rewrite/rerank still run at chat time.")
    for document in tqdm(documents, desc="Chunking documents"):
        chunks.extend(chunk_document_locally(document))
    return chunks


def create_embeddings(chunks):
    chroma = chroma_client()
    if COLLECTION_NAME in collection_names():
        chroma.delete_collection(COLLECTION_NAME)

    texts = [chunk.page_content for chunk in chunks]
    vectors = embed_texts(texts)
    collection = chroma.get_or_create_collection(COLLECTION_NAME)
    collection.add(
        ids=[str(i) for i in range(len(chunks))],
        embeddings=vectors,
        documents=texts,
        metadatas=[chunk.metadata for chunk in chunks],
    )
    print(f"Vectorstore created with {collection.count()} documents")


if __name__ == "__main__":
    documents = fetch_documents()
    chunks = create_chunks(documents)
    create_embeddings(chunks)
    print("Ingestion complete")
