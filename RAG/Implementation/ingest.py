import glob
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT.parent / ".env")
load_dotenv(ROOT / ".env")

DB_NAME = str(ROOT / "vector_db")
KNOWLEDGE_BASE = str(ROOT / "knowledge-base")
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

_embeddings = None


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings


def vectorstore_exists():
    db_path = Path(DB_NAME)
    if not db_path.exists():
        return False
    return any(db_path.iterdir())


def fetch_documents():
    folders = glob.glob(str(Path(KNOWLEDGE_BASE) / "*"))
    documents = []
    for folder in folders:
        if not os.path.isdir(folder):
            continue
        doc_type = os.path.basename(folder)
        loader = DirectoryLoader(
            folder,
            glob="**/*.md",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"},
        )
        folder_docs = loader.load()
        for doc in folder_docs:
            doc.metadata["doc_type"] = doc_type
            documents.append(doc)
    return documents


def create_chunks(documents):
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=200)
    return splitter.split_documents(documents)


def create_embeddings(chunks):
    if os.path.exists(DB_NAME):
        Chroma(persist_directory=DB_NAME, embedding_function=get_embeddings()).delete_collection()

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        persist_directory=DB_NAME,
    )
    count = vectorstore._collection.count()
    print(f"Stored {count:,} chunks in the vector database.")
    return vectorstore


def ensure_vectorstore():
    if not vectorstore_exists():
        documents = fetch_documents()
        if not documents:
            raise RuntimeError(f"No markdown files found in {KNOWLEDGE_BASE}.")
        chunks = create_chunks(documents)
        return create_embeddings(chunks)
    return Chroma(persist_directory=DB_NAME, embedding_function=get_embeddings())


if __name__ == "__main__":
    documents = fetch_documents()
    chunks = create_chunks(documents)
    create_embeddings(chunks)
    print("Ingestion complete")
