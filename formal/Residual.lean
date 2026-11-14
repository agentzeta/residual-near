/-
Residual: a Lean 4 model of the five-state classifier in residual/core.py (classify_account),
with machine-checked properties. Core Lean only; no Mathlib.

Scope (read before citing): these theorems are about this MODEL. The link to the Python code is
tests/test_formal_model.py, which checks every one of the 32 key-type combinations x 4 read
statuses against the truth table this file prints. Nothing here proves anything about NEAR
itself, RPC answers, or account security.
-/

inductive KeyType where
  | pqFull | pqFunction | classicalFull | classicalFunction | unknown
  deriving DecidableEq, Repr

inductive State where
  | classicalOnly | incompleteWeakestLink | complete | pqFunctionOnly | undetermined
  deriving DecidableEq, Repr

/-- Read outcome. `malformed` = the RPC answered but the key list was missing or not a list. -/
inductive Status where
  | ok | accountNotFound | rpcError | malformed
  deriving DecidableEq, Repr

open KeyType State Status

/-- Mirrors classify_account: the order of the checks is the order in core.py. -/
def classify : Status → List KeyType → State
  | ok, ks =>
    if ks = [] then undetermined
    else if unknown ∈ ks then undetermined
    else if classicalFull ∈ ks ∧ pqFull ∈ ks then incompleteWeakestLink
    else if classicalFull ∈ ks then classicalOnly
    else if pqFull ∈ ks then complete
    else if pqFunction ∈ ks then pqFunctionOnly
    else undetermined
  | _, _ => undetermined

/-- A failed or malformed read is never classified as anything but UNDETERMINED. -/
theorem failed_read_undetermined (s : Status) (ks : List KeyType) (h : s ≠ ok) :
    classify s ks = undetermined := by
  cases s <;> simp_all [classify]

/-- An unrecognized key always blocks classification: unknown is never counted as complete. -/
theorem unknown_never_complete (s : Status) (ks : List KeyType) (h : unknown ∈ ks) :
    classify s ks ≠ complete := by
  by_cases hn : ks = [] <;> by_cases hu : unknown ∈ ks <;> by_cases hc : classicalFull ∈ ks <;>
    by_cases hp : pqFull ∈ ks <;> by_cases hf : pqFunction ∈ ks <;> cases s <;> simp_all [classify]

/-- No account that holds a classical full-access key is ever counted as COMPLETE. -/
theorem classical_full_never_complete (s : Status) (ks : List KeyType) (h : classicalFull ∈ ks) :
    classify s ks ≠ complete := by
  by_cases hn : ks = [] <;> by_cases hu : unknown ∈ ks <;> by_cases hc : classicalFull ∈ ks <;>
    by_cases hp : pqFull ∈ ks <;> by_cases hf : pqFunction ∈ ks <;> cases s <;> simp_all [classify]

/-- Exact characterization of COMPLETE. -/
theorem complete_iff (s : Status) (ks : List KeyType) :
    classify s ks = complete ↔
      s = ok ∧ pqFull ∈ ks ∧ classicalFull ∉ ks ∧ unknown ∉ ks := by
  by_cases hn : ks = [] <;> by_cases hu : unknown ∈ ks <;> by_cases hc : classicalFull ∈ ks <;>
    by_cases hp : pqFull ∈ ks <;> by_cases hf : pqFunction ∈ ks <;> cases s <;> simp_all [classify]

/-- The thesis: adding an ML-DSA full-access key to a classical-only account yields the
mixed state, never COMPLETE. -/
theorem adding_pq_key_is_not_migration (ks : List KeyType)
    (h : classify ok ks = classicalOnly) :
    classify ok (pqFull :: ks) = incompleteWeakestLink := by
  by_cases hn : ks = [] <;> by_cases hu : unknown ∈ ks <;> by_cases hc : classicalFull ∈ ks <;>
    by_cases hp : pqFull ∈ ks <;> by_cases hf : pqFunction ∈ ks <;> simp_all [classify]

/-- Retiring every classical full-access key from a mixed account is what makes it COMPLETE. -/
theorem retiring_classical_keys_completes (ks : List KeyType)
    (h : classify ok ks = incompleteWeakestLink) :
    classify ok (ks.filter (· ≠ classicalFull)) = complete := by
  have hmix : unknown ∉ ks ∧ pqFull ∈ ks := by
    by_cases hn : ks = [] <;> by_cases hu : unknown ∈ ks <;> by_cases hc : classicalFull ∈ ks <;>
      by_cases hp : pqFull ∈ ks <;> by_cases hf : pqFunction ∈ ks <;> simp_all [classify]
  rw [complete_iff]
  refine ⟨rfl, ?_, ?_, ?_⟩
  · simp [List.mem_filter, hmix.2]
  · simp [List.mem_filter]
  · simp [List.mem_filter, hmix.1]

/-- Classification depends only on which key types are present, not on order or repeats. -/
theorem membership_only (s : Status) (ks ks' : List KeyType) (h : ∀ k, k ∈ ks ↔ k ∈ ks') :
    classify s ks = classify s ks' := by
  have hnil : ks = [] ↔ ks' = [] := by
    simp only [List.eq_nil_iff_forall_not_mem, h]
  cases s <;> simp only [classify, hnil, h]

/-! Truth table over all 32 presence patterns x 4 statuses, printed as JSON for the Python
cross-check. Regenerate with: lean formal/Residual.lean > formal/truth_table.json -/

def allTypes : List KeyType := [pqFull, pqFunction, classicalFull, classicalFunction, unknown]
def allStatuses : List Status := [ok, accountNotFound, rpcError, malformed]

def subsets : List KeyType → List (List KeyType)
  | [] => [[]]
  | x :: xs => (subsets xs).flatMap fun s => [s, x :: s]

def KeyType.name : KeyType → String
  | pqFull => "PQ_FULL" | pqFunction => "PQ_FUNCTION" | classicalFull => "CLASSICAL_FULL"
  | classicalFunction => "CLASSICAL_FUNCTION" | unknown => "UNKNOWN"

def State.name : State → String
  | classicalOnly => "CLASSICAL_ONLY" | incompleteWeakestLink => "INCOMPLETE_WEAKEST_LINK"
  | complete => "COMPLETE" | pqFunctionOnly => "PQ_FUNCTION_ONLY" | undetermined => "UNDETERMINED"

def Status.name : Status → String
  | ok => "OK" | accountNotFound => "ACCOUNT_NOT_FOUND" | rpcError => "RPC_ERROR" | malformed => "MALFORMED"

def quote (s : String) : String := "\"" ++ s ++ "\""

def row (s : Status) (ks : List KeyType) : String :=
  "{\"status\":" ++ quote s.name ++ ",\"key_types\":[" ++
    ",".intercalate (ks.map (quote ∘ KeyType.name)) ++ "],\"state\":" ++ quote (classify s ks).name ++ "}"

def truthTable : String :=
  "[\n" ++ ",\n".intercalate (allStatuses.flatMap fun s => (subsets allTypes).map (row s)) ++ "\n]"

#eval IO.println truthTable
