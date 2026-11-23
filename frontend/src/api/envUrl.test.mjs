/* eslint-disable no-undef */
// Run with: node --test frontend/src/api/envUrl.test.mjs
import assert from "node:assert/strict"
import test from "node:test"

// Mirrors envUrl() in src/api/client.ts. Kept as a plain copy so the rule can
// be tested without pulling in the whole module graph.
function envUrl(value, fallback) {
  const trimmed = value?.trim()
  return trimmed ? trimmed.replace(/\/+$/, "") : fallback
}

const LOCAL = "http://localhost:8000"

test("uses the variable when it is set", () => {
  assert.equal(envUrl("https://api.example.com", LOCAL), "https://api.example.com")
})

test("falls back when the variable is undefined", () => {
  assert.equal(envUrl(undefined, LOCAL), LOCAL)
})

test("falls back when the variable is an empty string", () => {
  // This is the bug that produced 405s: ?? does not catch "".
  assert.equal(envUrl("", LOCAL), LOCAL)
})

test("falls back when the variable is only whitespace", () => {
  assert.equal(envUrl("   ", LOCAL), LOCAL)
})

test("strips trailing slashes so paths never double up", () => {
  assert.equal(envUrl("https://api.example.com/", LOCAL), "https://api.example.com")
  assert.equal(envUrl("https://api.example.com///", LOCAL), "https://api.example.com")
})

test("keeps the scheme and host intact", () => {
  assert.equal(
    envUrl("https://studystack-auth.up.railway.app", LOCAL),
    "https://studystack-auth.up.railway.app",
  )
})
