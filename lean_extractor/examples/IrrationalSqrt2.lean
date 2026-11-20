import Mathlib.Data.Real.Irrational
import Mathlib.Data.Nat.Prime.Basic
import Mathlib.Tactic

/-- Classical proof of the irrationality of √2 via coprime integers and parity descent. -/
theorem irrational_sqrt_two : Irrational (Real.sqrt 2) := by
  intro ⟨q, hq⟩
  -- Write q = a / b in lowest terms with a : ℤ, b : ℕ, b > 0, and gcd(|a|, b) = 1
  have hcop : Nat.Coprime q.num.natAbs q.den := q.reduced
  have hb_pos : (0 : ℝ) < q.den := Nat.cast_pos.mpr q.pos
  -- Square both sides of (q : ℝ) = √2
  have hsq_real : ((q.num : ℝ) / (q.den : ℝ)) ^ 2 = 2 := by
    rw [← Rat.cast_def, hq, Real.sq_sqrt (by norm_num : (0 : ℝ) ≤ 2)]
  -- Clear denominators and pass to ℕ via |q.num|² = 2 * q.den²
  have hsq_nat : q.num.natAbs ^ 2 = 2 * q.den ^ 2 := by
    have hmul : (q.num : ℝ) ^ 2 = 2 * (q.den : ℝ) ^ 2 := by
      field_simp [ne_of_gt hb_pos] at hsq_real
      linarith
    have hint : q.num ^ 2 = 2 * (q.den : ℤ) ^ 2 := by exact_mod_cast hmul
    zify
    rw [sq_abs]
    exact hint
  -- Hence 2 divides |a|², and since 2 is prime, 2 divides |a|
  have h2_dvd_a_sq : 2 ∣ q.num.natAbs ^ 2 := ⟨q.den ^ 2, hsq_nat⟩
  have h2_dvd_a : 2 ∣ q.num.natAbs := Nat.Prime.dvd_of_dvd_pow Nat.prime_two h2_dvd_a_sq
  -- Write |a| = 2k and substitute back into |a|² = 2b²
  obtain ⟨k, hk⟩ := h2_dvd_a
  have h2b_sq : q.den ^ 2 = 2 * k ^ 2 := by
    rw [hk] at hsq_nat
    linarith
  -- Therefore 2 divides b², and again by primality of 2, 2 divides b
  have h2_dvd_b_sq : 2 ∣ q.den ^ 2 := ⟨k ^ 2, h2b_sq⟩
  have h2_dvd_b : 2 ∣ q.den := Nat.Prime.dvd_of_dvd_pow Nat.prime_two h2_dvd_b_sq
  -- This contradicts gcd(|a|, b) = 1 since 2 divides both |a| and b
  have h2_dvd_gcd : 2 ∣ Nat.gcd q.num.natAbs q.den := Nat.dvd_gcd h2_dvd_a h2_dvd_b
  rw [hcop.gcd_eq_one] at h2_dvd_gcd
  norm_num at h2_dvd_gcd
