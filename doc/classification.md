  Project Type Classification

  Your project is a Hybrid (INN + RES) project:
  ┌───────────────────┬────────────────┬──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │      Aspect       │ Classification │                                                             Evidence                                                             │
  ├───────────────────┼────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Innovation-driven │ Yes            │ Virtual Agent for Software Engineering - assists with code generation, test generation, code review, requirements, documentation │
  ├───────────────────┼────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Research-driven   │ Yes            │ Evaluation framework for LLM quality attributes (correctness, robustness, safety, hallucination)                                 │
  └───────────────────┴────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
  This matches exactly what the guidelines mention on page 5:
  "Virtual Agent for Software Engineering: Assist engineers to generate requirements, design, test cases, code analysis, attack scenarios and/or unsafe scenarios in any domain of interest (INN and/or RES)"

  ---
  Innovation-Driven Requirements Checklist
  ┌──────────────────────────┬────────────────────────────┬──────────────────────────────────────────────────────────────────┬────────┐
  │           Step           │          Required          │                           Your Project                           │ Status │
  ├──────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────────────┼────────┤
  │ 1. Requirements Analysis │ Stakeholder needs          │ Clear use case: developers needing AI-assisted coding            │ DONE   │
  ├──────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────────────┼────────┤
  │ 2. Design                │ Architecture choices       │ Well-defined: Agent Controller → Capabilities → RAG → Claude API │ DONE   │
  ├──────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────────────┼────────┤
  │ 3. Prototype Development │ Best-effort demo           │ FastAPI backend, 5 capabilities, RAG system, UI components       │ DONE   │
  ├──────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────────────┼────────┤
  │ 4. Testing - ML Accuracy │ Required                   │ Evaluation framework with 4 evaluators                           │ DONE   │
  ├──────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────────────┼────────┤
  │ 5. Testing - Quality     │ Safety, fairness, security │ SafetyEvaluator (security), HallucinationDetector                │ DONE   │
  ├──────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────────────┼────────┤
  │ 6. Local Deployment      │ Docker                     │ docker-compose.yml with 3 services                               │ DONE   │
  └──────────────────────────┴────────────────────────────┴──────────────────────────────────────────────────────────────────┴────────┘
  ---
  Research-Driven Requirements Checklist
  ┌───────────────────────────┬─────────────────────────┬─────────────────────────────────────────────────────────────────────────┬─────────┐
  │           Step            │        Required         │                              Your Project                               │ Status  │
  ├───────────────────────────┼─────────────────────────┼─────────────────────────────────────────────────────────────────────────┼─────────┤
  │ WHY: Problem Statement    │ Scientific problem      │ LLM code quality evaluation is an open challenge                        │ DONE    │
  ├───────────────────────────┼─────────────────────────┼─────────────────────────────────────────────────────────────────────────┼─────────┤
  │ WHY: Current Limitations  │ What's missing          │ Addresses hallucination, safety, robustness gaps                        │ DONE    │
  ├───────────────────────────┼─────────────────────────┼─────────────────────────────────────────────────────────────────────────┼─────────┤
  │ WHAT: Proposed Solution   │ Your approach           │ 4-evaluator framework with weighted scoring                             │ DONE    │
  ├───────────────────────────┼─────────────────────────┼─────────────────────────────────────────────────────────────────────────┼─────────┤
  │ HOW: Method               │ Implementation          │ Detailed evaluators: AST analysis, pattern matching, Bandit integration │ DONE    │
  ├───────────────────────────┼─────────────────────────┼─────────────────────────────────────────────────────────────────────────┼─────────┤
  │ HOW: Design of Experiment │ Confirm/reject solution │ Pipeline exists, but needs actual experiment results                    │ PARTIAL │
  └───────────────────────────┴─────────────────────────┴─────────────────────────────────────────────────────────────────────────┴─────────┘
  ---
  Evaluation Criteria Assessment
  ┌────────────────────┬────────────┬─────────────────────────────────────────────────────────────────┐
  │      Criteria      │   Status   │                              Notes                              │
  ├────────────────────┼────────────┼─────────────────────────────────────────────────────────────────┤
  │ Impact, Relevance  │ Strong     │ Directly addresses SE productivity with LLMs                    │
  ├────────────────────┼────────────┼─────────────────────────────────────────────────────────────────┤
  │ Correctness, Rigor │ Strong     │ Comprehensive evaluators with multiple detection layers         │
  ├────────────────────┼────────────┼─────────────────────────────────────────────────────────────────┤
  │ Originality        │ Good       │ Combined INN+RES approach with 4-dimensional quality assessment │
  ├────────────────────┼────────────┼─────────────────────────────────────────────────────────────────┤
  │ Presentation       │ Needs work │ Documentation exists but could use formal report                │
  ├────────────────────┼────────────┼─────────────────────────────────────────────────────────────────┤
  │ Reproducibility    │ Good       │ Docker deployment, config management, but tests are empty       │
  └────────────────────┴────────────┴─────────────────────────────────────────────────────────────────┘
  ---
  What's Missing / Needs Improvement
  ┌──────────────────────────┬──────────┬──────────────────────────────────────────────────────────────────────────────────┐
  │           Gap            │ Priority │                                  Recommendation                                  │
  ├──────────────────────────┼──────────┼──────────────────────────────────────────────────────────────────────────────────┤
  │ Unit Tests               │ HIGH     │ Tests directory is empty - need test coverage                                    │
  ├──────────────────────────┼──────────┼──────────────────────────────────────────────────────────────────────────────────┤
  │ Experimental Results     │ HIGH     │ Run the evaluation pipeline on actual code generation tasks and document results │
  ├──────────────────────────┼──────────┼──────────────────────────────────────────────────────────────────────────────────┤
  │ Formal Requirements Doc  │ MEDIUM   │ Add a requirements specification document                                        │
  ├──────────────────────────┼──────────┼──────────────────────────────────────────────────────────────────────────────────┤
  │ Design of Experiment     │ MEDIUM   │ Document hypothesis, metrics, datasets used for evaluation                       │
  ├──────────────────────────┼──────────┼──────────────────────────────────────────────────────────────────────────────────┤
  │ Research Findings Report │ MEDIUM   │ Summarize evaluation results (e.g., "Claude achieves X% correctness, Y% safety") │
  └──────────────────────────┴──────────┴──────────────────────────────────────────────────────────────────────────────────┘
  ---
  Summary
  ┌──────────────────────┬──────────────────────────────────────────────────┐
  │       Overall        │                    Assessment                    │
  ├──────────────────────┼──────────────────────────────────────────────────┤
  │ Guideline Compliance │ ~80% aligned                                     │
  ├──────────────────────┼──────────────────────────────────────────────────┤
  │ Core Structure       │ Fully matches the "Virtual Agent for SE" example │
  ├──────────────────────┼──────────────────────────────────────────────────┤
  │ INN Requirements     │ Mostly complete                                  │
  ├──────────────────────┼──────────────────────────────────────────────────┤
  │ RES Requirements     │ Framework exists, needs experimental validation  │
  └──────────────────────┴──────────────────────────────────────────────────┘
  Bottom Line: Your project structure is solid and aligns well with the guidelines. The main gaps are:
  1. Empty test suite - needs unit/integration tests
  2. No experimental results - need to run the evaluation framework and document findings
  3. Missing DoE documentation - formalize your research methodology
