import Mathlib.Data.Nat.Prime.Basic
import Mathlib.Data.Nat.Factorial.Basic
import Mathlib.Tactic

/-- Euclid's theorem: for every natural number n, there exists a prime p ≥ n. -/
theorem exists_infinite_primes (n : ℕ) : ∃ p, n ≤ p ∧ Nat.Prime p := by
  -- Consider N = n! + 1, which is strictly greater than 1
  let p := Nat.minFac (Nat.factorial n + 1)
  have hne : Nat.factorial n + 1 ≠ 1 := by
    have hpos : 0 < Nat.factorial n := Nat.factorial_pos n
    omega
  -- The smallest nontrivial factor p of n! + 1 is prime
  have hp_prime : Nat.Prime p := Nat.minFac_prime hne
  -- Show n ≤ p by contradiction: if p < n, then p divides both n! and n! + 1
  have hge : n ≤ p := by
    by_contra hlt
    push_neg at hlt
    have hp_dvd_fac : p ∣ Nat.factorial n :=
      Nat.dvd_factorial hp_prime.pos (le_of_lt hlt)
    have hp_dvd_succ : p ∣ Nat.factorial n + 1 := Nat.minFac_dvd _
    have hp_dvd_one : p ∣ 1 := (Nat.dvd_add_right hp_dvd_fac).mp hp_dvd_succ
    exact hp_prime.not_dvd_one hp_dvd_one
  exact ⟨p, hge, hp_prime⟩
