# Creating a Widget System

This document summarizes the design guidance from the conversation about building a siloed widget system in an SSR WSGI app.

## Goals

- Keep widgets top-to-bottom siloed
- Make pages compose widgets without embedding widget internals
- Pass explicit context into widgets
- Keep widgets reusable, testable, and isolated
- Support optional discovery/manifest-driven composition

## Widget design principles

- Each widget should be its own module with logic and rendering responsibilities.
- Page endpoints should be orchestrators only, not a place for widget business logic.
- Widgets should receive context explicitly, not parse raw `environ` or URL structures.
- External dependencies like logging, database access, and rendering should be abstracted and injected.
- Widgets should validate required context and fail gracefully when it is missing.
- Widget templates should generally live with the widget code so the widget remains self-contained.

## Recommended widget structure

- `widgets/<widget_name>.py`
  - define required context fields
  - accept a shared context object
  - fetch or render its own data
  - return HTML fragments or data for template rendering

- Page handler:
  - parse route parameters, query params, and auth claims
  - construct `page_context`
  - discover required widgets
  - call each widget with context
  - render the final page using widget fragments

## Context and external data

- Important values like `product_id` should be extracted by the page or middleware layer.
- Those values should be placed into `page_context` and passed into widgets.
- Widgets can then call services with the provided IDs, rather than reading URLs directly.

## Widget manifest and discovery

- A manifest system is useful when widget composition is dynamic or reusable across pages.
- A manifest can declare:
  - page → widget list
  - slots/regions
  - order
  - conditional rules (roles, feature flags, viewport hints)
- A discovery service can map pages and context to widget descriptors.

## Viewport and layout concerns

- Widgets can carry layout hints like `slot`, `priority`, and `responsive` categories.
- They should not own pixel-level layout or CSS behavior.
- Actual rendering and responsive behavior should stay in templates/CSS.
- Multiple widget templates for mobile/desktop are acceptable only when markup differences are meaningful.

## Error handling and graceful failure

- Widgets should detect missing required context and render a safe fallback.
- They should log the missing context for developers without breaking the full page.
- Failures should be explicit and controlled, not raw exceptions visible to the user.

## Testability

- Abstract data sources, logging, and output mechanisms.
- Inject dependencies into widgets instead of using global or environment-specific objects.
- This makes widgets easy to unit test and keeps the system modular.

## When to use a manifest or discovery service

- Use them when you need:
  - flexible page/widget composition
  - centralized control of widget placement
  - dynamic widget selection based on context
- Avoid them if your app is small and widget composition is fixed.

## Summary

- Keep page handlers as orchestration layers.
- Keep widgets independent and context-driven.
- Use a manifest/discovery layer when composition needs to be declarative.
- Keep layout hints lightweight and leave actual rendering to templates.
- Abstract data/logging to preserve testability.
- Gracefully handle missing widget context.
