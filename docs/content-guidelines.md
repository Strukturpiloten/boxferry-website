# Documentation style

Public documentation helps a user finish a task. It is not a project diary or a book.

## Page structure

1. State the outcome in the first two sentences.
2. Put prerequisites before the first command.
3. Show the smallest complete input and one copyable command.
4. Show the output tree or result users should verify.
5. Add only the failure guidance relevant to that task.
6. Link to reference material instead of repeating it.

Use tutorials for the first success, guides for tasks, concepts for decisions, and reference pages
for exact contracts. Keep Lens documentation below the secondary Libraries section.

## Writing

- Prefer short sentences, active voice, concrete nouns, and exact option names.
- Use one idea per paragraph and descriptive headings.
- Delete introductions that repeat the title.
- Do not publish roadmaps, implementation history, generic encouragement, or placeholder copy.
- Do not claim compatibility that is not backed by a target profile and tests.
- Keep pages below 900 words and prose paragraphs below 120 words. Generated rule pages are smaller.

## Examples and reference data

Every displayed `boxferry` command has an example ID in the BoxFerry-owned
`docs/documentation-examples.toml`. BoxFerry executes those commands in black-box tests. The website
checks the same command blocks before building.

Diagnostic pages are generated from the checked CLI rule catalogue. Do not hand-copy the 52 rule
descriptions into Markdown.

## Ownership

The repository that owns behavior owns its technical Markdown and executable examples. The website
repository owns navigation, presentation, assembly, legal pages, and these writing rules.
