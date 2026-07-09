import pytest
from app.services import ai_service


def test_extract_amount_usd_dollar():
    assert ai_service._extract_amount("I have $320 to invest") == ("$", 320.0)
    assert ai_service._extract_amount("I have 500 dollars") == ("$", 500.0)


def test_extract_amount_inr():
    assert ai_service._extract_amount("I have $10000") == ("$", 10000.0)
    assert ai_service._extract_amount("I have 2000 rupees") == ("$", 2000.0)


def test_generate_affordable_suggestions_small_amount():
    txt = ai_service._generate_affordable_suggestions("$", 320)
    assert "Based on your budget" in txt
    # should include at least one ticker suggestion
    assert "AAPL" in txt or "AMD" in txt or "INTC" in txt


def test_generate_affordable_suggestions_large_amount():
    txt = ai_service._generate_affordable_suggestions("$", 2000)
    assert "Based on your budget" in txt
    # with larger budget, NVDA may be included in suggestions
    assert any(sym in txt for sym in ["AAPL", "MSFT", "TSLA", "NVDA", "VOO"])


def test_build_trade_payload_without_amount():
    payload = ai_service._build_trade_payload("BUY", "AAPL")
    assert payload["symbol"] == "AAPL"
    assert payload["tradeType"] == "buy"
    assert payload["qty"] == 1.0
    assert "/dashboard/trading?symbol=AAPL&tradeType=buy&qty=1.0" in payload["url"]


def test_build_trade_payload_with_amount():
    payload = ai_service._build_trade_payload("BUY", "AAPL", ("$", 320.0))
    assert payload["symbol"] == "AAPL"
    assert payload["tradeType"] == "buy"
    assert payload["qty"] == 2.13
    assert "/dashboard/trading?symbol=AAPL&tradeType=buy&qty=2.13" in payload["url"]
