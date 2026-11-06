# Fresh gather-free logf/log source and host accuracy

Both changed sources replace only indexed table loads with fixed register
shards, preserving the original Arm table bits, FP expression order and special
paths. Original sources and outcomes remain immutable. These are HOST results;
G5 remains1/36 and neither log target export is qualified.

| Changed source | Fresh active/inactive lanes | Finite nearest-word histogram | Maximum checked changed-word ULP |
|---|---:|---:|---:|
| logf16SP |1871180/571044|1007997exact+3152one-step|0.7753994128742986|
| log8DP |1385603/21357|867091exact+102one-step|0.510228845583582|

Each changed algorithm ran ONE owned SSE2/noAVX/noFMA/contractionoff host
compile/execution, nearest-even/FTZDAZoff. Zero value/exception/profile/merge/
empty-mask mismatches. logf covers65536masks/3aliases; log covers256/3aliases.
Cached inputs and independent rounded references were authenticated; only
changed finite results received fresh independent interval evaluation. Old
algorithms and old outputs were not executed/read.

logf result9ec612f0 SHAd7ef129a23ead2781c6b7ab28cfbfb85ff5d56c279558cc21d73caf305ecb19c;
log result19c40d9e SHAfa9283b1f55b4e2f1f39c907b1bdfb986bbb7a8b6b6e7ccd0c7b334e1b365268.
Four NEW assessor groups each pass: logf4dab59e2,log a2c3d391. New table controls
check actual parsed changed constants against original scalar data: logf32
payloads/512field-lane-index selections7e617598; log512payloads/4096selections
414dee30. The initial logf source-identity note recorded256assignments but only
performed32reconstructions; it is excluded as lane-assignment evidence and
superseded by7e617598. No numerical/compiler output was replayed to correct it.

Each changed export was emitted ONCE by the unchanged Linux-target compiler:
logf9821261a/result1fae29d7, rawf5becafc (0gathers,69unknown/21names);
log2c265e41/resultbfd9136d, raw21612a20 (0gathers,281unknown/40names).
These actual retained queues are the work list; do not rerun unchanged emissions
or reports. Target templates, whole-image/static/call ABI, fresh>=1e6card-lane
assessment and the remaining36-export matrix stay open.
