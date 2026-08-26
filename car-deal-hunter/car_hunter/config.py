import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=True)

DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

HF_DATASET = "Yoad22/craigslist-used-cars-eda"

MIN_PRICE = 1_000
MAX_PRICE = 80_000
MIN_YEAR = 1995
MAX_ODOMETER = 250_000

LITE_TRAIN = 8_000
LITE_VAL = 1_000
LITE_TEST = 1_000

QUESTION = "What does this used car cost to the nearest dollar?"
PREFIX = "Price is $"

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
SPECIALIST_ADAPTER = os.getenv("SPECIALIST_ADAPTER", str(DATA_DIR / "qlora_adapter"))
DEAL_THRESHOLD = float(os.getenv("DEAL_THRESHOLD", "1500"))

CHROMA_PATH = DATA_DIR / "chroma"
COLLECTION_NAME = "used_cars"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

TRAIN_PATH = DATA_DIR / "train.parquet"
VAL_PATH = DATA_DIR / "val.parquet"
TEST_PATH = DATA_DIR / "test.parquet"
RF_PATH = DATA_DIR / "random_forest.joblib"
METRICS_PATH = DATA_DIR / "metrics.json"
ALERTS_PATH = DATA_DIR / "alerts.jsonl"
