import '@testing-library/jest-dom/vitest'
import { afterAll, afterEach, beforeAll } from 'vitest'

import { server } from './msw/server'

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

// jsdom doesn't implement the Pointer Events / scroll APIs Radix UI's interactive
// components (Select, Dropdown, etc.) rely on -- without these, clicking to open one
// throws "target.hasPointerCapture is not a function" rather than testing anything
// real about the app. Standard, widely-used polyfill for jsdom + Radix.
if (typeof Element !== 'undefined') {
  Element.prototype.hasPointerCapture ??= () => false
  Element.prototype.setPointerCapture ??= () => {}
  Element.prototype.releasePointerCapture ??= () => {}
  Element.prototype.scrollIntoView ??= () => {}
}
