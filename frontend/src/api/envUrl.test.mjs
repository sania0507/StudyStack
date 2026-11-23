/* eslint-disable no-undef */
// Run with: node --test frontend/src/api/envUrl.test.mjs
import assert from "node:assert/strict"
import test from "node:test"

// Mirrors envUrl() in src/api/client.ts. Kept as a plain copy so the rule can
// be tested without pulling in the whole module graph.
function envUrl(value, fallback) {
  const trimmed = value?.trim()
  if (!trimmed) return fallback

  const withScheme = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`

  return withScheme.replace(/\/+$/, "")
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

test("adds https:// when the variable has no scheme", () => {
  // This is the bug that glued the Railway host onto the Vercel URL as a path.
  assert.equal(
    envUrl("studystack-production-444688f5.up.railway.app", LOCAL),
    "https://studystack-production-444688f5.up.railway.app",
  )
})

test("adds https:// and still strips a trailing slash", () => {
  assert.equal(
    envUrl("studystack-production-444688f5.up.railway.app/", LOCAL),
    "https://studystack-production-444688f5.up.railway.app",
  )
})

test("leaves an http:// scheme alone rather than forcing https", () => {
  assert.equal(envUrl("http://localhost:8000", LOCAL), "http://localhost:8000")
})

test("the resolved URL is always absolute, never a path", () => {
  const cases = [
    "studystack-production-444688f5.up.railway.app",
    "https://studystack-production-444688f5.up.railway.app",
    "  studystack-production-444688f5.up.railway.app  ",
  ]

  for (const value of cases) {
    const result = envUrl(value, LOCAL)
    assert.ok(
      /^https?:\/\//.test(result),
      `expected an absolute URL, got ${JSON.stringify(result)}`,
    )
  }
})
