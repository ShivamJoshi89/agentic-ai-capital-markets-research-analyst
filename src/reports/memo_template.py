"""
Investment memo template
"""

MEMO_TEMPLATE = """
# Investment Research Memo: {company_name} ({ticker})

## Executive Summary
{executive_summary}

## 1. Company Overview
{company_overview}

## 2. Market Performance
{market_performance}

## 3. Financial Fundamentals
{fundamentals}

## 4. News and Sentiment
{news_sentiment}

## 5. Macroeconomic Context
{macro_context}

## 6. Key Risk Factors
{risks}

## 7. Bull Case
{bull_case}

## 8. Base Case
{base_case}

## 9. Bear Case
{bear_case}

## 10. Final Summary
{final_summary}

---

**Disclaimer:** This research memo is for educational purposes only and should not be 
considered investment advice. Always consult with qualified financial professionals 
before making investment decisions.

**Generated:** {generated_date}
**Confidence Score:** {confidence_score}%
"""