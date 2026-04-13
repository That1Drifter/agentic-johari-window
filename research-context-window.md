# Context Window Problems in LLMs: Research Survey

*Research conducted April 11, 2026. Focused on 2023-2026 literature.*

## Executive Summary

The literature strongly supports treating context window quality as a first-order problem in LLM systems. The v0.2 Agentic Johari Window framing (Signal/Bloat/Needed/Unknown) aligns well with how the field has converged, though the terminology differs. The Chroma team's 2025 "context rot" research confirmed that every frontier model tested (18 models, ~194K LLM calls) degrades as input tokens increase, even on trivially simple tasks. The "lost in the middle" effect (Liu et al. 2023) has been partially mitigated in newer models but not eliminated. The field has moved from "prompt engineering" to "context engineering" (term popularized by Shopify CEO Tobi Lutke, June 2025), which is essentially what the v0.2 framework formalizes. The claim that bloat actively creates the Needed quadrant is well-supported: irrelevant tokens don't just waste space, they actively mislead models through distractor interference and attention dilution. The three forces (Pruning, Retrieval, Exploration) map onto active research areas with real tooling (LLMLingua for pruning, RAG for retrieval, memory systems for exploration), though no unified framework ties them together the way v0.2 proposes.

---

## 1. Lost in the Middle / Attention Degradation

The canonical finding comes from Liu et al. (2023), "Lost in the Middle: How Language Models Use Long Contexts" (arXiv:2307.03172). They tested multi-document QA and key-value retrieval, finding a U-shaped performance curve: models attend best to the beginning and end of input, with accuracy dropping 30%+ when relevant information sits in positions 5-15 out of 20 documents. This holds even for models explicitly trained on long contexts.

**Has it been fixed?** Partially. The Databricks blog (2024) reported that GPT-4o, Claude 3.5 Sonnet, and GPT-4o-mini show "little to no performance deterioration" on long-context tasks compared to earlier models. Hsieh et al.'s RULER benchmark (2024, arXiv:2404.06654) found that while models pass simple needle-in-a-haystack, they fail badly on harder retrieval tasks (multi-hop tracing, aggregation) as context grows. Only half of models claiming 32K+ context maintain satisfactory performance at 32K on RULER tasks. "Found in the Middle" (Hsieh et al. 2024, ACL Findings, arXiv:2406.16008) identified the root cause as intrinsic U-shaped attention bias and proposed a calibration mechanism that improved RAG performance by up to 15 percentage points.

**Attention sinks**: Xiao et al. (2023), "Efficient Streaming Language Models with Attention Sinks" (arXiv:2309.17453, ICLR 2024). They discovered that LLMs dump disproportionate attention on the first token regardless of its semantic relevance. This is a SoftMax artifact: attention scores must sum to 1, so the model uses early tokens as a "sink" for excess attention. StreamingLLM exploits this by keeping initial tokens as anchors, enabling stable inference over 4M+ tokens with 22x speedup over sliding-window baselines.

**v0.2 alignment**: The attention degradation literature directly supports the Bloat quadrant. Content in the middle of the window occupies space but receives diminished attention, making it functionally invisible. It's present but not processed. The v0.2 insight that bloat *creates* the Needed quadrant is validated here: middle-positioned information is simultaneously "in the window" and "effectively absent."

---

## 2. Context Window Compression and Its Failure Modes

**LLMLingua family (Microsoft, 2023-2024)**: LLMLingua (EMNLP 2023, arXiv:2310.05736) uses a small language model (GPT-2 or LLaMA-7B) to identify and remove unimportant tokens, achieving 20x compression with only 1.5% performance loss on GSM8K. LongLLMLingua (ACL 2024) extends this with question-aware compression and document reordering, achieving 21.4% improvement on multi-document QA while using only 25% of tokens. LLMLingua-2 further improves with data distillation for task-agnostic compression.

**Learned compression**: ICAE (In-context Autoencoder, arXiv:2307.06945) compresses long contexts into compact "memory slots" using LoRA fine-tuning (~1% additional parameters), achieving 4x compression on Llama. AutoCompressors (Chevalier et al. 2023) recursively compress text into summary vectors. Gist tokens (Mu et al. 2023) achieve prompt compression by fine-tuning an LLM to produce compressed token representations. Activation Beacon (2024, arXiv:2401.03462) offers another approach via activation-level compression.

**What gets lost**: Summarization-based compression (the most common production approach) is inherently lossy. Details get compressed away, minority viewpoints in long feedback collections get silenced, and specific numerical or temporal details are the first casualties. Aggressive compression improves cost but damages factual accuracy. Cutting context too aggressively forces re-fetching, which can cost more than the tokens saved. Naive strategies like token truncation lose critical details for long-horizon reasoning (Nayak 2026, Medium).

**v0.2 alignment**: Compression is a Pruning force that attempts to shrink Bloat. But imperfect compression creates a new failure mode: it can accidentally move Signal into the Unknown quadrant (information that was known, got compressed away, and is now lost). The v0.2 framework would predict this, since pruning without understanding relevance is destructive.

---

## 3. Context Rot / Stale Context

"Context rot" is now a recognized term, formalized by the Chroma research team in their July 2025 technical report, "Context Rot: How Increasing Input Tokens Impacts LLM Performance" (Hong, Troynikov, Huber). They tested 18 frontier models (Claude Opus 4, GPT-4.1, Gemini 2.5 Pro, Qwen3-235B, and others) across ~194,480 LLM calls.

**Key findings**: Every model degrades as input length increases. This is not context overflow (exceeding the window) but degradation well before the limit. A model with a 200K window can show significant degradation at 50K tokens. Three compounding mechanisms drive it: (1) lost-in-the-middle attention bias, (2) attention dilution (quadratic scaling means 100K tokens = 10 billion pairwise relationships), (3) distractor interference (semantically similar but irrelevant content actively misleads). Counterintuitively, shuffled haystacks outperform structured ones, suggesting attention mechanisms are sensitive to contextual patterns in ways that can hurt.

**Model-specific patterns**: Claude models decay slowest overall but refuse tasks at length thresholds (~2.89% refusal rate for Opus). GPT models show erratic, inconsistent outputs. Gemini models produce random words starting around 500-750 word lengths in replication tasks. Performance collapse isn't gradual but shows inflection points.

**Practitioner experience**: The term has spread rapidly through practitioner communities. Redis published a guide on preventing context rot (2025). Multiple blog posts document long-conversation degradation in coding agents, where accumulated search/exploration noise degrades every subsequent output. The morphllm.com guide distinguishes "compaction" (removing tokens while preserving meaning) from "summarization" (generating new text that describes old text), noting different failure modes for each.

**v0.2 alignment**: Context rot is the Bloat quadrant in action. The v0.2 framework captures this precisely: stale context is "present in window" but "wrong/stale," and it actively degrades performance on remaining Signal. The Chroma finding that distractor interference is a primary mechanism directly supports the claim that bloat creates the Needed quadrant.

---

## 4. RAG Failure Modes: When Retrieval Adds Bloat

Barnett et al. (2024), "Seven Failure Points When Engineering a RAG Pipeline" (arXiv:2401.05856, CAIN 2024), identified seven failure points from three real-world case studies:

1. **FP1 - Missing Content**: Question cannot be answered from available documents; system hallucinates.
2. **FP2 - Missed Top Ranked**: Relevant document exists but doesn't rank in top-K.
3. **FP3 - Not in Context**: Answer retrieved but filtered out during consolidation.
4. **FP4 - Not Extracted**: Answer is in context but LLM fails to extract it (noise/contradictions).
5. **FP5 - Wrong Format**: LLM ignores formatting instructions.
6. **FP6 - Incorrect Specificity**: Too much or too little detail.
7. **FP7 - Incomplete**: Answer partially extracted despite full information being available.

FP2-FP4 are directly relevant to the v0.2 framework. FP2 is a Retrieval failure (information stays in Needed). FP3 is a Pruning failure that moves Signal to Needed. FP4 is the Bloat problem, where noise prevents extraction of present Signal.

**RAG vs. long context**: The "RAG is dead" debate intensified after Gemini 1.5 Pro's 1M-token window (Feb 2024). The consensus as of 2026: naive RAG is dead, but sophisticated RAG is thriving. RAG is ~1,250x cheaper per query than stuffing everything into long context. RAG framework usage surged 400% since 2024, with 60% of production LLM applications now using it (RAGFlow 2025 review). Long context works for static datasets under 100 documents / 100K tokens. Beyond that, RAG wins on cost but introduces its own failure modes. The emerging view: RAG is a "context engine" not just a "retrieval engine," and the focus should be on quality of retrieved context, not quantity.

**Robustness research**: Yoran et al. (2023, arXiv:2310.01558) proposed NLI-based filtering to make retrieval-augmented LMs robust to irrelevant context. AttentionRAG (2025, arXiv:2503.10720) prunes context based on attention patterns. RankRAG (NeurIPS 2024) unifies ranking with generation. The trend is toward models that can selectively attend to relevant retrieved chunks and ignore noise.

**v0.2 alignment**: RAG is the primary Retrieval force, but the failure mode taxonomy shows that retrieval without quality control can increase Bloat instead of shrinking Needed. The v0.2 framework predicts this: moving information from Unknown/Needed into the window only helps if it lands in Signal, not Bloat.

---

## 5. Selective Attention and Long-Context Evaluation

**Needle-in-a-haystack limitations**: The standard NIAH test (find a single fact in padding) is too easy. Most frontier models score near-perfect. RULER (Hsieh et al. 2024, COLM 2024, arXiv:2404.06654) introduced 13 tasks across 4 categories (retrieval, multi-hop tracing, aggregation, QA) with configurable length/complexity. Results: despite near-perfect NIAH scores, almost all models show large performance drops as context grows. Only half maintain satisfactory performance at their claimed context sizes.

**Can models learn to ignore irrelevant context?** Active research area. Layer-based knowledge guidance (ACL Findings 2025) examines attention patterns across layers, finding earlier layers focus on syntax while deeper layers capture semantics. Document reordering strategies place high-relevance documents at beginning/end positions to exploit positional bias rather than fight it. Fine-tuning for robustness (training with noisy retrievals) shows promise but doesn't fully solve the problem.

**Instruction following under load**: Research confirms that instruction-following degrades with more context. "Boosting Instruction Following at Scale" (arXiv:2510.14842) introduced instruction boosting as a test-time correction strategy, gaining up to 7 percentage points on multi-instruction tasks. This suggests the problem is real and persistent.

**v0.2 alignment**: The gap between NIAH scores and RULER performance maps exactly onto the difference between "information is present" and "information is effectively usable." The v0.2 framework captures this: Signal requires both presence AND relevance. Bloat is present but not relevant. The evaluation literature confirms that current models cannot reliably distinguish Signal from Bloat on their own.

---

## 6. Memory Systems as Context Management

**MemGPT / Letta**: Packer et al. (2023), "MemGPT: Towards LLMs as Operating Systems" (arXiv:2310.08560). Treats the context window as "physical memory" and external storage as "virtual memory," using function calls to page information in and out. Four memory tiers: core (always present), message (recent conversation), archival (long-term storage), recall (search-indexed history). Now the Letta framework, with DeepLearning.AI offering a course on the approach.

**Production memory frameworks**: Zep uses temporal knowledge graphs, storing facts with validity windows ("Kendra loves Adidas shoes as of March 2026"). On LongMemEval with GPT-4o, Zep scores 63.8% vs. Mem0's 49.0%. Mem0 optimizes for simplicity and scale, using intelligent filtering to reduce redundant API calls. Key architectural tension: systems that aggressively compress (Mem0) achieve smaller context windows but risk losing detail; systems that preserve raw data maintain integrity but need efficient retrieval.

**Claude Memory**: Anthropic launched Claude Memory in September 2025, expanding to all users by March 2026. Uses a transparent, file-based approach (CLAUDE.md Markdown files) rather than vector databases. Three-layer architecture: persistent memory file, grep-based search, and (unshipped) background daemon. Notable limitation: as memory files grow, the model's ability to find relevant information within the memory block diminishes, a phenomenon users call "fading memory." This is context rot applied to the memory system itself.

**v0.2 alignment**: Memory systems are mechanisms for managing the boundary between Needed and Signal. MemGPT's paging metaphor maps directly: "paging in" is Retrieval (Needed to Signal), "paging out" is Pruning (Bloat removal). The "fading memory" problem in Claude Memory is the v0.2 framework's core insight: accumulating context without pruning creates Bloat that degrades access to Signal.

---

## 7. MCP and Structured Context Protocols

The Model Context Protocol (MCP) was announced by Anthropic in November 2024 as an open standard for connecting AI assistants to external data. By December 2025, it was donated to the Agentic AI Foundation (Linux Foundation) for vendor-neutral governance. Adoption has been massive: 97M+ monthly SDK downloads, backing from Anthropic, OpenAI, Google, and Microsoft. Tens of thousands of MCP servers exist.

**MCP as context management**: MCP provides structured context delivery: resources (data), tools (actions), and prompts (templates) are delivered in typed, scoped formats rather than dumped as raw conversation text. This is architecturally significant for context quality because structured delivery allows the model to receive exactly the context it needs for a specific operation, rather than carrying accumulated conversation history.

**RAG-MCP** (Gao et al. 2025, arXiv:2505.03275): Addresses "prompt bloat" from MCP tool descriptions. As MCP servers proliferate (0 to 4,400+ in 5 months), listing all tool descriptions in the prompt creates massive bloat. RAG-MCP uses semantic retrieval to select only relevant tool descriptions, cutting prompt tokens by 50%+ and tripling tool selection accuracy (43.13% vs 13.62% baseline).

**v0.2 alignment**: MCP is fundamentally a context quality protocol. It enables targeted Retrieval (pulling specific resources into the window) over unstructured accumulation. RAG-MCP directly addresses the Bloat quadrant by pruning irrelevant tool descriptions. The v0.2 framework would classify MCP resources as a mechanism for moving information from Needed to Signal with minimal Bloat, which is precisely its design intent.

---

## 8. The Zero-Sum Tradeoff: CoT vs. Task Content

**CoT can hurt**: "Mind Your Step (by Step): Chain-of-Thought can Reduce Performance on Tasks where Thinking Makes Humans Worse" (arXiv:2410.21333, 2024) found that CoT decreases performance on tasks where verbal reasoning hurts humans too (e.g., facial recognition). The constraint is fundamental: reasoning tokens consume context budget.

**Token budget research**: "Token-Budget-Aware LLM Reasoning" (ACL Findings 2025, arXiv:2412.18547) showed that a reasonable token budget (50 tokens) reduces output from 258 to 86 tokens while maintaining correctness, but smaller budgets (10 tokens) backfire (157 tokens output, worse quality). Dynamic budget allocation based on problem complexity is the emerging approach.

**System prompt bloat**: Practitioner consensus (MLOps Community 2025, multiple blog posts): optimal system prompt is 150-300 words; above 500 words, diminishing returns and instruction dilution begin. Long system prompts hurt the prefill phase, slow time-to-first-token, bloat the KV cache, and interact badly with lost-in-the-middle effects. Recommended budget: no more than 5-10% of total context window for system prompt. RAG-MCP found that tool descriptions alone can consume massive prompt space, a form of system prompt bloat.

**v0.2 alignment**: This is the zero-sum nature of the context window made explicit. Every token of CoT reasoning, system prompt, or tool description is a token that could hold task-relevant Signal. The v0.2 framework captures this through the displacement mechanism: Bloat doesn't just waste space, it pushes Signal out. System prompt bloat is a special case because it's *permanent* bloat, present in every turn, creating a fixed tax on the Signal budget.

---

## Synthesis

### What the literature supports in v0.2

1. **The four-quadrant framing is well-grounded.** Signal (relevant + present), Bloat (irrelevant + present), Needed (relevant + absent), and Unknown (irrelevant + absent) correspond to real, measurable phenomena in the literature. Context rot research confirms Bloat is measurably harmful. RULER and long-context evaluation confirm the gap between "present" and "usable." RAG failure modes confirm the Needed quadrant is real.

2. **The displacement claim is validated.** The Chroma context rot study's "distractor interference" finding directly supports the claim that bloat creates the Needed quadrant. Irrelevant tokens don't just waste space, they actively mislead through attention dilution and semantic interference. This is the strongest finding for the v0.2 framework.

3. **The three forces map onto real tooling.** Pruning (LLMLingua, conversation compression, context compaction), Retrieval (RAG, MCP resources, memory recall), and Exploration (web search, tool use, memory discovery) are all active research and engineering areas. No existing framework unifies them the way v0.2 proposes.

4. **"Context engineering" is the emerging umbrella.** The field has independently converged on treating context management as a first-class engineering discipline (Lutke 2025, LangChain, Anthropic docs). The v0.2 framework provides a more structured mental model than the loose "context engineering" label.

### What's under-studied

1. **Bloat measurement.** No standard metric for "what percentage of my context window is Bloat vs. Signal." The Chroma study measures degradation but not the composition of the context that causes it. A Bloat Index would be a novel contribution.

2. **Pruning-Retrieval interaction.** Most research treats pruning and retrieval independently. The v0.2 insight that overpruning creates Needed (requiring retrieval) and over-retrieval creates Bloat (requiring pruning) is intuitive but not empirically studied as a feedback loop.

3. **The Unknown quadrant.** By definition, you don't know what you don't know. Exploration is the least-studied force. Research on agentic discovery, curiosity-driven search, and proactive information gathering is nascent.

4. **Temporal dynamics.** Context quality changes over a conversation. Early context may start as Signal and become Bloat (stale decisions, superseded plans). No formal model tracks this degradation over time, though Zep's temporal knowledge graphs are a step.

### Opportunities for v0.2

- Provide the unifying framework that "context engineering" currently lacks
- Introduce measurable quadrant composition (Signal%, Bloat%, etc.) as a diagnostic tool
- Formalize the displacement mechanism as a testable hypothesis
- Connect the three forces to specific failure modes (pruning failures, retrieval failures, exploration failures) with actionable guidance
- Position against MemGPT's OS metaphor: MemGPT is about paging mechanics, v0.2 is about what should be paged and why

---

## References

1. Liu, N.F., Lin, K., Hewitt, J., Paranjape, A., Bevilacqua, M., Petroni, F., Liang, P. (2023). "Lost in the Middle: How Language Models Use Long Contexts." arXiv:2307.03172. https://arxiv.org/abs/2307.03172

2. Xiao, G., Tian, Y., Chen, B., Han, S., Lewis, M. (2023). "Efficient Streaming Language Models with Attention Sinks." ICLR 2024. arXiv:2309.17453. https://arxiv.org/abs/2309.17453

3. Hsieh, C.-P., Sun, S., et al. (2024). "RULER: What's the Real Context Size of Your Long-Context Language Models?" COLM 2024. arXiv:2404.06654. https://arxiv.org/abs/2404.06654

4. Hsieh, C.-P. et al. (2024). "Found in the Middle: Calibrating Positional Attention Bias Improves Long Context Utilization." ACL Findings 2024. arXiv:2406.16008. https://arxiv.org/abs/2406.16008

5. Jiang, Z., et al. (2023). "LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models." EMNLP 2023. arXiv:2310.05736. https://arxiv.org/abs/2310.05736

6. Jiang, Z., et al. (2024). "LongLLMLingua: Accelerating and Enhancing LLMs in Long Context Scenarios via Prompt Compression." ACL 2024. https://aclanthology.org/2024.acl-long.91.pdf

7. Ge, T., et al. (2023). "In-context Autoencoder for Context Compression in a Large Language Model." arXiv:2307.06945. https://arxiv.org/abs/2307.06945

8. Hong, K., Troynikov, A., Huber, J. (2025). "Context Rot: How Increasing Input Tokens Impacts LLM Performance." Chroma Technical Report. https://www.trychroma.com/research/context-rot

9. Barnett, S., et al. (2024). "Seven Failure Points When Engineering a Retrieval Augmented Generation System." CAIN 2024. arXiv:2401.05856. https://arxiv.org/abs/2401.05856

10. Packer, C., Wooders, S., Lin, K., Fang, V., Patil, S.G., Gonzalez, J.E. (2023). "MemGPT: Towards LLMs as Operating Systems." arXiv:2310.08560. https://arxiv.org/abs/2310.08560

11. Gao, Y., et al. (2025). "RAG-MCP: Mitigating Prompt Bloat in LLM Tool Selection via Retrieval-Augmented Generation." arXiv:2505.03275. https://arxiv.org/abs/2505.03275

12. Han, C., et al. (2024). "Token-Budget-Aware LLM Reasoning." ACL Findings 2025. arXiv:2412.18547. https://arxiv.org/abs/2412.18547

13. Marjanovic, O., et al. (2024). "Mind Your Step (by Step): Chain-of-Thought can Reduce Performance on Tasks where Thinking Makes Humans Worse." arXiv:2410.21333. https://arxiv.org/abs/2410.21333

14. Yoran, O., et al. (2023). "Making Retrieval-Augmented Language Models Robust to Irrelevant Context." ICLR 2025. arXiv:2310.01558. https://arxiv.org/abs/2310.01558

15. Databricks (2024). "Long Context RAG Performance of LLMs." https://www.databricks.com/blog/long-context-rag-performance-llms

16. RAGFlow (2025). "From RAG to Context: A 2025 Year-End Review of RAG." https://ragflow.io/blog/rag-review-2025-from-rag-to-context

17. Valbuena, L. (2025). "Why Long System Prompts Hurt Context Windows (and How to Fix It)." Medium / Data Science Collective. https://medium.com/data-science-collective/why-long-system-prompts-hurt-context-windows-and-how-to-fix-it-7a3696e1cdf9

18. MLOps Community (2025). "The Impact of Prompt Bloat on LLM Output Quality." https://mlops.community/the-impact-of-prompt-bloat-on-llm-output-quality/

19. Anthropic (2024). "Model Context Protocol." https://modelcontextprotocol.io/

20. Mem0 Inc. (2025). "Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory." arXiv:2504.19413. https://arxiv.org/abs/2504.19413

21. Zep (2025-2026). Context Engineering & Agent Memory Platform. https://www.getzep.com/

22. Nayak, P. (2026). "Automatic Context Compression in LLM Agents." Medium / The AI Forum. https://medium.com/the-ai-forum/automatic-context-compression-in-llm-agents-why-agents-need-to-forget-and-how-to-help-them-do-it-43bff14c341d

23. Chevalier, A., et al. (2023). "Adapting Language Models to Compress Contexts." EMNLP 2023. (AutoCompressors)

24. Mu, J., Li, X., Goodman, N. (2023). "Learning to Compress Prompts with Gist Tokens." NeurIPS 2023.

25. Skywork AI (2025). "Claude Memory: A Deep Dive into Anthropic's Persistent Context Solution." https://skywork.ai/blog/claude-memory-a-deep-dive-into-anthropics-persistent-context-solution/

26. Atlan (2026). "Best AI Agent Memory Frameworks 2026: Mem0, Zep, LangChain, Letta." https://atlan.com/know/best-ai-agent-memory-frameworks-2026/
