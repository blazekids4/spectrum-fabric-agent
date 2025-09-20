Excellent — you’re thinking in the right direction. To stress-test an LLM’s consistency and tuning, you want to give it prompts that **simulate SQL-like structured queries** (counts, sums, comparisons) *and* **open-ended or reasoning queries** that go beyond SQL (causal, narrative, comparative, hypothetical).

Here’s a structured list of prompts broken into two groups:

---

## 🔹 SQL-Style Prompts (LLM should behave like a database query engine)

These test whether the LLM can return **consistent numeric answers**:

1. **Basic count/lookup**

   * “What was the number of T-Mobile mentions in week 2025-W34?”
   * “How many times was Verizon mentioned in 2025-W31?”

2. **Aggregations**

   * “What is the total number of mentions of T-Mobile across all 12 weeks?”
   * “Which brand had the highest total mentions across all weeks?”
   * “Calculate the average weekly mentions for AT\&T.”

3. **Comparisons**

   * “In week 2025-W30, how many more mentions did T-Mobile have compared to AT\&T?”
   * “Which brand had the largest increase in mentions from W26 to W37?”

4. **Filters + conditions**

   * “List all the promotions that led to more than 300 switches to a brand.”
   * “Which weeks did Dish Wireless have more than 100 mentions?”

5. **Top-N queries**

   * “What were the top 3 most mentioned competitors in week 2025-W32?”
   * “Rank all brands by their total switches to brand across 12 weeks.”

---

## 🔹 Beyond SQL Prompts (LLM reasoning, context, narrative, causality)

These test whether the LLM can **summarize, explain patterns, and infer insights**:

1. **Trend detection**

   * “Explain the trend of T-Mobile mentions over the 12 weeks — is it increasing, decreasing, or fluctuating?”
   * “Which competitor shows the most consistent growth in mentions across the dataset?”

2. **Promo impact analysis**

   * “Which T-Mobile promotions appear to have driven the largest switching gains?”
   * “Compare how Verizon’s NFL Sunday Ticket promos impacted mentions versus T-Mobile’s iPhone 15 promos.”

3. **Comparative storytelling**

   * “Summarize how T-Mobile’s competitive position shifted over the 12 weeks compared to AT\&T and Verizon.”
   * “Which competitor looks most vulnerable based on switches from brand vs. to brand?”

4. **Cause-and-effect style reasoning**

   * “Why might T-Mobile’s mentions spike during week 2025-W30?”
   * “What could explain Dish Wireless losing more customers than it gained across most weeks?”

5. **Hypothetical / simulation**

   * “If T-Mobile continued gaining mentions at the same rate as the past 3 weeks, how many mentions would they have by week 2025-W40?”
   * “If Verizon’s NFL promos ended after W34, predict how their mentions might change in following weeks.”

6. **Business intelligence style summary**

   * “Give me an executive summary of the competitive landscape in this dataset: who leads, who lags, and why.”
   * “Provide a SWOT analysis for T-Mobile based on mentions and switching behavior across the 12 weeks.”

---

⚖️ **Why this matters:**

* SQL-style prompts ensure *numerical consistency* (tests whether the LLM is hallucinating counts).
* Beyond-SQL prompts test *reasoning ability* (LLM’s added value over just running queries).
* Using both sets together reveals how well your LLM balances deterministic retrieval with interpretive insight.