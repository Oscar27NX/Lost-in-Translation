import Mathlib.Analysis.SpecificLimits.Basic
import Mathlib.Algebra.BigOperators.Group.Finset
import Mathlib.Tactic

open Finset BigOperators

/-- Partial sum H_N = ∑_{k=1}^{N} 1/k of the harmonic series. -/
noncomputable def harmonicSum (N : ℕ) : ℝ :=
  ∑ k ∈ Finset.Icc 1 N, (1 : ℝ) / (k : ℝ)

/-- Oresme's dyadic block lower bound: H_{2^n} ≥ 1 + n / 2 for all n ∈ ℕ. -/
lemma harmonicSum_two_pow_ge (n : ℕ) :
    1 + (n : ℝ) / 2 ≤ harmonicSum (2 ^ n) := by
  induction n with
  | zero =>
    -- Base case n = 0: H_1 = 1 ≥ 1 + 0/2
    simp [harmonicSum]
  | succ n ih =>
    -- Split H_{2^(n+1)} into H_{2^n} plus the dyadic block (2^n, 2^(n+1)]
    have hsplit : harmonicSum (2 ^ (n + 1)) =
        harmonicSum (2 ^ n) + ∑ k ∈ Finset.Ioc (2 ^ n) (2 ^ (n + 1)), (1 : ℝ) / k := by
      unfold harmonicSum
      rw [← Finset.sum_Icc_add_sum_Ioc (Nat.pow_le_pow_right (by norm_num) (Nat.le_succ n))]
    -- On (2^n, 2^(n+1)], every term satisfies 1/k ≥ 1 / 2^(n+1)
    have hterm : ∀ k ∈ Finset.Ioc (2 ^ n) (2 ^ (n + 1)),
        (1 : ℝ) / (2 ^ (n + 1) : ℝ) ≤ (1 : ℝ) / (k : ℝ) := by
      intro k hk
      have hk_pos : (0 : ℝ) < (k : ℝ) := by
        exact_mod_cast lt_of_le_of_lt (Nat.zero_le _) (Finset.mem_Ioc.mp hk).1
      have hk_le : (k : ℝ) ≤ (2 ^ (n + 1) : ℝ) := by
        exact_mod_cast (Finset.mem_Ioc.mp hk).2
      exact one_div_le_one_div_of_le hk_pos hk_le
    -- Sum the lower bound over the 2^n terms of the dyadic block
    have hblock : (1 : ℝ) / 2 ≤ ∑ k ∈ Finset.Ioc (2 ^ n) (2 ^ (n + 1)), (1 : ℝ) / (k : ℝ) := by
      have hcard : (Finset.Ioc (2 ^ n) (2 ^ (n + 1))).card = 2 ^ n := by
        rw [Nat.card_Ioc, pow_succ]
        omega
      calc (1 : ℝ) / 2
          = (2 ^ n : ℝ) * ((1 : ℝ) / (2 ^ (n + 1) : ℝ)) := by
              rw [pow_succ]; field_simp
        _ = ∑ _k ∈ Finset.Ioc (2 ^ n) (2 ^ (n + 1)), (1 : ℝ) / (2 ^ (n + 1) : ℝ) := by
              rw [Finset.sum_const, nsmul_eq_mul, hcard]
        _ ≤ ∑ k ∈ Finset.Ioc (2 ^ n) (2 ^ (n + 1)), (1 : ℝ) / (k : ℝ) :=
              Finset.sum_le_sum hterm
    -- Combine inductive hypothesis ih with the block bound hblock
    rw [hsplit]
    push_cast
    linarith

/-- Divergence of the harmonic series: partial sums exceed every real bound M. -/
theorem harmonic_series_diverges : ∀ M : ℝ, ∃ N : ℕ, M < harmonicSum N := by
  intro M
  obtain ⟨n, hn⟩ := exists_nat_gt (2 * M)
  refine ⟨2 ^ n, ?_⟩
  have hge := harmonicSum_two_pow_ge n
  linarith
