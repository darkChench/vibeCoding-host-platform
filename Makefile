# Makefile for Vibe Coding Guide

.PHONY: help lint check-links check-details check-doc-structure check-directory-docs check-metadata check-ai-citation check-wiki sync-doc-toc build test clean clean-deps

MARKDOWNLINT = npx --yes markdownlint-cli@0.48.0

help:
	@echo "Makefile for Vibe Coding Guide"
	@echo ""
	@echo "Available commands:"
	@echo "  help     - Show this help message"
	@echo "  lint     - Lint all markdown files"
	@echo "  build    - Verify knowledge base has no build step"
	@echo "  test     - Run repository quality gates"
	@echo "  clean    - Remove ignored generated caches"
	@echo "  clean-deps - Remove local dependency caches"
	@echo ""

lint:
	@echo "Linting markdown files..."
	@$(MARKDOWNLINT) --config .github/lint_config.json --ignore .history --ignore tools/external '**/*.md'

build:
	@echo "No build step: this repository is a documentation and knowledge-base project."

test: lint check-links check-details check-doc-structure check-directory-docs check-metadata check-ai-citation
	@echo "Quality gates complete."

clean-deps:
	@echo "Cleaning local dependency caches..."
	@rm -rf node_modules
	@echo "Dependency cleanup complete."
