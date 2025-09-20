# **paired test harness** where each test case has two parts

1. **SQL Baseline Prompt** → numeric/structured answer (like what a query engine should return).
2. **LLM Narrative Prompt** → reasoning, causality, or storytelling that _uses_ the structured result as context.

This will let you check both **accuracy** (did the model get the numbers right?) and **added value** (did the model explain them in a meaningful way?).

---

# 📊 Paired Test Harness

### **Test 1: Weekly Lookup**

- **SQL Baseline Prompt:**
  _“What was the number of T-Mobile mentions in week 2025-W34?”_
- **LLM Narrative Prompt:**
  _“How might the promotions listed for T-Mobile in week 2025-W34 have contributed to its mention volume?”_

---

### **Test 2: Total Mentions**

- **SQL Baseline Prompt:**
  _“What is the total number of mentions for Verizon across all 12 weeks?”_
- **LLM Narrative Prompt:**
  _“What does this total tell us about Verizon’s competitive standing compared to T-Mobile and AT\&T?”_

---

### **Test 3: Comparisons**

- **SQL Baseline Prompt:**
  _“In week 2025-W30, how many more mentions did T-Mobile have compared to AT\&T?”_
- **LLM Narrative Prompt:**
  _“What could explain the difference in mentions between T-Mobile and AT\&T during week 2025-W30?”_

---

### **Test 4: Aggregations**

- **SQL Baseline Prompt:**
  _“Which brand had the highest average mentions per week across the dataset?”_
- **LLM Narrative Prompt:**
  _“Summarize what this reveals about long-term customer attention trends in the industry.”_

---

### **Test 5: Switching Behavior**

- **SQL Baseline Prompt:**
  _“Which brand gained the most switches-to-brand in week 2025-W32?”_
- **LLM Narrative Prompt:**
  _“Based on the promotion driving those switches, explain why customers may have chosen that brand.”_

---

### **Test 6: Trend Detection**

- **SQL Baseline Prompt:**
  _“Show the week-over-week change in mentions for T-Mobile between W28 and W32.”_
- **LLM Narrative Prompt:**
  _“Describe whether this indicates momentum building for T-Mobile and what risks could stall that momentum.”_

---

### **Test 7: Top-N**

- **SQL Baseline Prompt:**
  _“Rank all brands by their total mentions from highest to lowest.”_
- **LLM Narrative Prompt:**
  _“Narratively explain what this ranking suggests about the competitive landscape.”_

---

### **Test 8: Hypothetical Forecasting**

- **SQL Baseline Prompt:**
  _“What was the average increase in T-Mobile mentions per week between W30 and W37?”_
- **LLM Narrative Prompt:**
  _“If that increase continues, how many mentions would T-Mobile have by W40, and what business opportunities could this create?”_

---

### **Test 9: Promo Impact**

- **SQL Baseline Prompt:**
  _“List all T-Mobile promotions that led to more than 300 switches in a given week.”_
- **LLM Narrative Prompt:**
  _“Which of these promotions appears most effective, and what does that tell us about customer priorities?”_

---

### **Test 10: Executive Summary**

- **SQL Baseline Prompt:**
  _“What are the total switches-to-brand and switches-from-brand for each competitor across all 12 weeks?”_
- **LLM Narrative Prompt:**
  _“Using those totals, write a concise executive summary highlighting winners, losers, and potential threats in the marketplace.”_

---

⚖️ **How to Use This Harness**

- Run **both prompts per test** on your LLM.
- Check if the **SQL-style numeric answer** matches ground truth from your dataset.
- Then check whether the **narrative answer** is both factually consistent with the numbers _and_ provides useful business insight.
