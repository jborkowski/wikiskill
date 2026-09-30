// Run with subagent({workflow:"./eval/benchmarks/code-review/compare.js",
// args:{repoRoot:"<checkout>",fixtureRoot:"<build_fixtures.py output>"},
// context:"fresh",async:true,globalConcurrencyLimit:5,maxSubagentSpawnsPerRun:5}).
const variants = [
  {key:"baseline", path:"baseline.md", axis:"all"},
  {key:"two-standards", path:"two-axis.md", axis:"Standards"},
  {key:"two-spec", path:"two-axis.md", axis:"Spec"},
  {key:"hybrid-standards", path:"hybrid.md", axis:"Standards"},
  {key:"hybrid-behavior", path:"hybrid.md", axis:"Spec/Behavior"}
];
const results = await runs.all(variants.map(v => ({
  key:v.key, label:"Benchmark " + v.key + " coverage", agent:"delegate",
  task:"Read-only benchmark review. Read procedure " + args.repoRoot +
    "/eval/benchmarks/code-review/variants/" + v.path + " and manifest " +
    args.fixtureRoot + "/manifest.json. Review all four fixture repositories at exact " +
    "base/head supplied. User supplies base as fixed point and explicit SPEC.md where " +
    "present; null confirms no spec. Execute only assigned axis: " + v.axis +
    ". For all, execute entire baseline. Supervisor handles parallel orchestration; " +
    "do not spawn children. Do not read build_fixtures.py, truth.json, other variants, " +
    "or other reports. Inspect diffs, callers, and context directly. No project edits, " +
    "code execution, network, installs, commits, or publishing. Return per case scope " +
    "SHAs, findings with lines, severity, rule/spec/behavior evidence, optional smells " +
    "separately, checks and limitations. No findings is valid. Supplied-version reports " +
    "stay under 400 words per case. Stop/report inaccessible refs. Perform actual " +
    "review, not skill critique or guesses about benchmark expectations.",
  output:"reviews/" + v.key + ".md"
})));
return results.map(r => ({output:r.output, outputReference:r.outputReference,
  artifactPaths:r.artifactPaths}));
