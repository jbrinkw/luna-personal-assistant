# Luna: A Personal Assistant Platform and Research Playground

Luna is a platform for building personal assistants that use natural language to operate large, extensible toolbases. The default extension set focuses on offloading everyday planning, tracking, and execution so you can stay healthy, organized, and effective with minimal cognitive load.

At its core, Luna aims to:

- Make it effortless to ask for anything in plain language and have the agent route to the right tools
- Support an arbitrarily large and evolving set of tools and domains
- Be easy to extend and customize for new workflows
- Serve as a research sandbox for fast, natural human–agent interaction across big toolbases

## What’s included (first-class extensions)

- CoachByte: fitness planning, training splits, set timers, and workout tracking
- ChefByte: nutrition and meal planning to keep diet on track
- GeneralByte: everyday personal assistant tasks and utilities
- Notes: Obsidian-based note integration and project organization
- Home Assistant: smart home interactions
- Todo List: lightweight task capture and follow-through

These are designed to cover daily life basics while showcasing how to structure richer domain tools. As needs grow, add new extensions without changing the agent’s core contract.

## How it works (at a glance)

- Natural-language first: you describe goals; the agent plans and chooses tools
- Tool orchestration: agents can query, combine, and reason over multiple domains
- Minimal interface: a small, stable agent I/O spec for easy interoperability
- Speed and transparency: return times and tool traces for insight and iteration

## Why this project

Most assistants are either too narrow or too hard to extend. Luna is meant to be both a capable daily assistant and a flexible foundation for new functionality. Initially, tools emphasize student and researcher workflows, with an explicit path to grow into a great assistant for anyone.

Secondary goal: provide a practical research platform for techniques that make interacting with large toolbases feel fast and natural—reducing friction between the human’s intent and the agent’s actions.

## Explore next

- Getting started: installation, running, and quick usage
- Core → Agent Format: agent interface and configuration
- Core → Extension Format: adding and organizing extensions
- Core → Agents: available agent strategies and when to use them

Docs style: detailed but concise. If something is unclear or missing, open an issue or PR.
