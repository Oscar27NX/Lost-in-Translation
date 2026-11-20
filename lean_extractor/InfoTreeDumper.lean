/-
  Lost In Translation — Lean 4 InfoTree Extractor
  ================================================
  Elaborates a Lean 4 source file via `Elab.runFrontend` and traverses every
  `Lean.Elab.InfoTree` emitted by the elaborator, printing a canonical JSON
  document containing:
    - exact 1-based line/column spans (`FileMap.toPosition`)
    - tactic syntax kind and source slice
    - pretty-printed goalsBefore and goalsAfter (`Meta.ppGoal`)
    - hypothesis bindings and target propositions
    - referenced constant names in each tactic term

  Usage:
    lake build infotree_dumper
    lake exe infotree_dumper path/to/Proof.lean
-/
import Lean

open Lean Elab Meta

namespace LostInTranslation

structure HypothesisJson where
  name : String
  type : String
  deriving ToJson

structure GoalJson where
  tag : String
  hypotheses : Array HypothesisJson
  target : String
  pretty : String
  deriving ToJson

structure TacticNodeJson where
  nodeId : String
  parentId : Option String
  depth : Nat
  kind : String
  tacticKind : String
  startLine : Nat
  startCol : Nat
  endLine : Nat
  endCol : Nat
  sourceSlice : String
  goalsBefore : Array GoalJson
  goalsAfter : Array GoalJson
  referencedConstants : Array String
  deriving ToJson

structure InfoTreeDocJson where
  filePath : String
  leanVersion : String
  extractorMode : String
  nodes : Array TacticNodeJson
  deriving ToJson

/-- Extract structured hypotheses and target from a single `MVarId`. -/
def dumpGoal (mvarId : MVarId) : MetaM GoalJson := do
  mvarId.withContext do
    let decl ← mvarId.getDecl
    let lctx ← getLCtx
    let mut hyps : Array HypothesisJson := #[]
    for ldecl in lctx do
      if !ldecl.isImplementationDetail then
        let tyFmt ← ppExpr (← instantiateMVars ldecl.type)
        hyps := hyps.push {
          name := ldecl.userName.toString
          type := tyFmt.pretty
        }
    let targetFmt ← ppExpr (← instantiateMVars decl.type)
    let fullFmt ← ppGoal mvarId
    return {
      tag := decl.userName.toString
      hypotheses := hyps
      target := targetFmt.pretty
      pretty := fullFmt.pretty
    }

/-- Pretty-print a list of goal metavariables inside the recorded `ContextInfo` and `MetavarContext`. -/
def dumpGoals (ci : ContextInfo) (mctx : MetavarContext) (goals : List MVarId) : IO (Array GoalJson) := do
  let mut out : Array GoalJson := #[]
  for g in goals do
    let res ← ci.runMetaM {} do
      withMCtx mctx do
        try
          some <$> dumpGoal g
        catch _ =>
          pure none
    if let some gj := res then
      out := out.push gj
  return out

/-- Collect constant names appearing in a tactic's elaborated term context if present. -/
def collectSyntaxIdentNames (stx : Syntax) : Array String :=
  Id.run do
    let mut acc : Array String := #[]
    let rec go (s : Syntax) : StateM (Array String) Unit := do
      match s with
      | .ident _ _ val _ =>
        modify fun a => if a.contains val.toString then a else a.push val.toString
      | .node _ _ args =>
        for arg in args do
          go arg
      | _ => pure ()
    let (_, finalAcc) := (go stx).run acc
    return finalAcc

/-- Recursively traverse an `InfoTree` and emit `TacticNodeJson` entries. -/
partial def walkTree
    (fileMap : FileMap)
    (source : String)
    (ctx? : Option ContextInfo)
    (parentId : Option String)
    (depth : Nat)
    (counter : IO.Ref Nat)
    (acc : IO.Ref (Array TacticNodeJson))
    (tree : InfoTree) : IO Unit := do
  match tree with
  | .context ci t =>
    walkTree fileMap source (ci.mergeIntoOuter? ctx?) parentId depth counter acc t
  | .node info children =>
    let mut nextParent := parentId
    let mut nextDepth := depth
    if let some ci := ctx? then
      if let .ofTacticInfo ti := info then
        if let (some startPos, some endPos) := (ti.stx.getPos?, ti.stx.getTailPos?) then
          let p1 := fileMap.toPosition startPos
          let p2 := fileMap.toPosition endPos
          let idx ← counter.modifyGet fun n => (n + 1, n + 1)
          let nid := s!"n{idx}"
          let slice := (source.extract startPos endPos).trim
          let before ← dumpGoals ci ti.mctxBefore ti.goalsBefore
          let after ← dumpGoals ci ti.mctxAfter ti.goalsAfter
          let refs := collectSyntaxIdentNames ti.stx
          let node : TacticNodeJson := {
            nodeId := nid
            parentId := parentId
            depth := depth
            kind := "tactic"
            tacticKind := ti.stx.getKind.toString
            startLine := p1.line
            startCol := p1.column + 1
            endLine := p2.line
            endCol := p2.column + 1
            sourceSlice := slice
            goalsBefore := before
            goalsAfter := after
            referencedConstants := refs
          }
          acc.modify (·.push node)
          nextParent := some nid
          nextDepth := depth + 1
    for child in children do
      walkTree fileMap source ctx? nextParent nextDepth counter acc child
  | .hole _ => pure ()

def dumpFile (path : System.FilePath) : IO InfoTreeDocJson := do
  initSearchPath (← findSysroot)
  let source ← IO.FS.readFile path
  let fileMap := FileMap.ofString source
  let opts := Options.empty.setBool `linter.unusedVariables false
  let (env, ok) ← Elab.runFrontend source opts path.toString `LostInTranslationTarget
  let _ := (env, ok)
  -- To capture the full PersistentArray of InfoTrees from FrontendM directly:
  let inputCtx := Parser.mkInputContext source path.toString
  let (header, parserState, messages) ← Parser.parseHeader inputCtx
  let (env', messages) ← Elab.processHeader header opts messages inputCtx
  let cmdState := Command.mkState env' messages opts
  let cmdState := { cmdState with infoState := { cmdState.infoState with enabled := true } }
  let frontState ← IO.processCommands inputCtx parserState cmdState
  let counter ← IO.mkRef 0
  let acc ← IO.mkRef #[]
  for tree in frontState.commandState.infoState.trees do
    walkTree fileMap source none none 0 counter acc tree
  let nodes ← acc.get
  return {
    filePath := path.toString
    leanVersion := Lean.versionString
    extractorMode := "lean4_infotree"
    nodes := nodes
  }

end LostInTranslation

def main (args : List String) : IO UInt32 := do
  match args with
  | [filePath] =>
    let doc ← LostInTranslation.dumpFile filePath
    IO.println (Lean.toJson doc).pretty
    return 0
  | _ =>
    IO.eprintln "Usage: lake exe infotree_dumper <path/to/file.lean>"
    return 1
