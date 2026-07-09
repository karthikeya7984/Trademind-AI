"""
Financial News Sentiment Analysis
Uses HuggingFace FinBERT for domain-specific sentiment.
"""
from typing import List
import re


class SentimentAnalyzer:
    """FinBERT-based financial sentiment analyzer."""

    def __init__(self):
        self.pipeline = None
        self._load_model()

    def _load_model(self):
        try:
            from transformers import pipeline
            self.pipeline = pipeline(
                "text-classification",
                model="ProsusAI/finbert",
                tokenizer="ProsusAI/finbert",
                max_length=512,
                truncation=True,
            )
        except Exception:
            self.pipeline = None

    def analyze(self, text: str) -> dict:
        """Analyze sentiment of financial text."""
        if self.pipeline:
            try:
                result = self.pipeline(text[:512])[0]
                label_map = {"positive": 1.0, "negative": -1.0, "neutral": 0.0}
                return {
                    "sentiment": result["label"],
                    "score": round(result["score"], 3),
                    "numeric": label_map.get(result["label"], 0.0),
                }
            except Exception:
                pass

        return self._rule_based(text)

    def _rule_based(self, text: str) -> dict:
        """Fallback rule-based sentiment."""
        text_lower = text.lower()
        positive = {"surge", "gain", "rise", "bull", "growth", "profit", "beat", "strong", "rally", "soar"}
        negative = {"fall", "drop", "loss", "bear", "decline", "miss", "weak", "crash", "plunge", "slump"}

        words = set(re.findall(r'\w+', text_lower))
        pos_count = len(words & positive)
        neg_count = len(words & negative)

        if pos_count > neg_count:
            return {"sentiment": "positive", "score": 0.7, "numeric": 1.0}
        elif neg_count > pos_count:
            return {"sentiment": "negative", "score": 0.7, "numeric": -1.0}
        return {"sentiment": "neutral", "score": 0.6, "numeric": 0.0}

    def batch_analyze(self, texts: List[str]) -> List[dict]:
        return [self.analyze(t) for t in texts]

    def aggregate_sentiment(self, texts: List[str]) -> dict:
        """Aggregate sentiment across multiple articles."""
        results = self.batch_analyze(texts)
        if not results:
            return {"overall": "neutral", "score": 0.0, "breakdown": {}}

        scores = [r["numeric"] for r in results]
        avg = sum(scores) / len(scores)
        overall = "positive" if avg > 0.1 else "negative" if avg < -0.1 else "neutral"

        breakdown = {
            "positive": sum(1 for r in results if r["sentiment"] == "positive"),
            "negative": sum(1 for r in results if r["sentiment"] == "negative"),
            "neutral": sum(1 for r in results if r["sentiment"] == "neutral"),
        }

        return {"overall": overall, "score": round(avg, 3), "breakdown": breakdown, "total": len(results)}
