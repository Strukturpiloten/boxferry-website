---
title: BoxFerry
description: Reliable N:N conversion of container application definitions
hide:
  - navigation
  - toc
---

<div class="bf-home">
  <section class="bf-hero">
    <p class="bf-eyebrow">Container definitions, carried safely</p>
    <h1>Convert container applications without losing sight of their intent.</h1>
    <p class="bf-lead">
      BoxFerry is an open-source N:N converter for Compose and Quadlet. It explains unsupported,
      approximated, and omitted intent instead of silently discarding it.
    </p>
    <div class="bf-actions">
      <a class="md-button md-button--primary" href="docs/getting-started/">Get started</a>
      <a class="md-button" href="https://github.com/Strukturpiloten/boxferry">View on GitHub</a>
    </div>
  </section>

  <section class="bf-command" aria-labelledby="first-command">
    <div>
      <p class="bf-eyebrow">A direct route</p>
      <h2 id="first-command">Start with one explicit conversion</h2>
      <p>Input and output formats are visible in the command, and route-specific help stays focused.</p>
    </div>

    ```console
    boxferry convert compose quadlet \
      --input-file compose.yaml \
      --output-directory quadlet
    ```

  </section>

  <section class="bf-grid" aria-label="BoxFerry principles">
    <article>
      <h2>N:N by design</h2>
      <p>Read and write every supported format, including canonical same-format output.</p>
    </article>
    <article>
      <h2>Explain every loss</h2>
      <p>Stable diagnostic rules identify conversion boundaries and put blocking fixes first.</p>
    </article>
    <article>
      <h2>Privacy by default</h2>
      <p>Reports classify sensitive values, alias paths, and exclude raw input and environment data.</p>
    </article>
  </section>

  <section class="bf-maintainer">
    <p class="bf-eyebrow">Built in the open</p>
    <h2>Maintained by Strukturpiloten and the BoxFerry community</h2>
    <p>
      BoxFerry is community software maintained by Strukturpiloten OHG. Professional service details
      will be added after their scope and support contract are defined.
    </p>
  </section>
</div>
