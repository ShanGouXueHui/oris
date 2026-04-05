# Decision: use Gemini automatically while Zhipu is blocked by insufficient balance
Date: 2026-04-06

## Context
The direct provider probe layer was extended to Gemini and Zhipu.
Gemini probe succeeded.
Zhipu probe no longer fails because of wrong model naming; it now fails because the account has insufficient balance / no usable resource package.

## Decision
1. Keep Gemini in the automatic routing pool immediately.
2. Allow Gemini to serve as:
   - free fallback
   - CN candidate substitute
3. Do not wait for Zhipu manually.
4. Resume Zhipu automatically once quota or balance becomes available and probe becomes healthy.

## Outcome
ORIS can continue to work automatically without human intervention, even though Zhipu is currently unavailable for commercial reasons.
