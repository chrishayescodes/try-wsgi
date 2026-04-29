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

## Extensibility and creating new widgets

The value of a widget system is that new widgets can be created independently and registered without changing core page logic.

A concrete new-widget creation flow:

1. Create the widget module
   - add `widgets/<widget_name>.py`
   - define a widget entry point like `render_widget(context, services)`
   - list required context fields explicitly

2. Add the widget template
   - place `widgets/<widget_name>.html` next to the module
   - keep markup scoped to the widget
   - use the same renderer/interface as other widgets

3. Define widget metadata
   - add a manifest entry or registration object
   - include `module`, `template`, `slots`, `order`, and `conditions`
   - declare required context and optional layout hints

4. Register the widget
   - add it to the discovery/manifest config
   - keep page handlers unaware of widget internals
   - let the discovery service decide when and where to include it

5. Write tests
   - unit-test the widget logic independently
   - test missing context fallback behavior
   - test the widget template rendering if possible

6. Document the widget contract
   - explain required context values
   - note injected dependencies such as `renderer`, `logger`, or data services
   - make widget ownership clear for future contributors

This approach keeps new widget work isolated: authors touch only widget code, widget templates, manifest registration, and tests. Existing pages and shared infrastructure remain unchanged unless new widget requires new context values.

## Widget ecosystem and documentation

A healthy widget system is more than code; it is an ecosystem of documentation and conventions.

- Provide a widget README or contributor guide.
  - explain the widget lifecycle
  - document how pages discover and render widgets
  - include the manifest/registration format
- Describe how to use widgets in pages.
  - show examples of page context construction
  - explain slot names and rendering order
  - include auth/context requirements
- Document setup for widget authors.
  - how to add new widget modules and templates
  - how to register widgets in the manifest or discovery service
  - how to add required context values when needed
- Include guidance for creating custom widgets.
  - required context contract
  - dependency injection patterns
  - graceful failure behavior
  - testing strategy
- Treat widgets as reusable components, not ad-hoc page fragments.
  - keep the contract stable
  - keep the documentation with the widget ecosystem
  - make it easy for contributors to add widgets without deep framework knowledge

This ecosystem mindset makes the widget system easier to adopt, maintain, and extend.

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
