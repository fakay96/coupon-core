import { describe, it, expect } from 'vitest'
import { simplifyErrors } from '../index'

describe('simplifyErrors', () => {
  it('flattens error messages', () => {
    const errors = { email: ['Invalid'], password: ['Too short'] }
    expect(simplifyErrors(errors)).toBe('email: Invalid | password: Too short')
  })

  it('returns empty string for invalid input', () => {
    expect(simplifyErrors(null as any)).toBe('')
  })
})
