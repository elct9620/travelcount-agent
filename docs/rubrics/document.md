# Document Rubric

To keep document clearify, conciseness and consistency, use the following rubric to evaluate the quality of the document.

## Criteria

### Consistency

The document should follow the `docs/template/[type].md` structure, and not contain any additional sections or headings beyond those specified in the template.
The sections only allowed to extend when template use `[SECTION_1]`, `[SECTION_2]`, etc.

> If no template exists for the document type, make minimal changes to the existing structure, ensuring clarity and logical flow of information.

### Clarity and Conciseness

The document should be written in clear and concise language, avoiding unnecessary jargon or complex sentences.
All information should based on the referenced sources or convensation context.

For example, the `docs/design/` usually created based on `docs/features/` and `docs/ARCHITECTURE.md`. The the content should not infer non-existing concepts or features.

### References

When document is created based on other documents or sources, it should include proper references to those sources.

For example, the design document should use `[feature](../features/[feature_name].md)` links to reference the features it is based on.

- Do not mention line numbers or specific sections that may change over time.
- Do not take note on the document, e.g. `xxx.py (existing)`

## Scoring

Each criteria is binarily scored as either 0 (does not meet expectations) or 1 (meets expectations). When over 80% of the criteria are met, the document is considered to have passed the rubric evaluation.
