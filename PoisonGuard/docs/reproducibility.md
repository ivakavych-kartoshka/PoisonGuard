# Reproducibility

Use Python 3.11+, create an isolated environment, install `.[dev]`, and run `python -m pytest -q`. The local validation also exercised the code on Python 3.9.6 for compatibility; that older interpreter is not the declared support target.

All randomness begins with the YAML seed. The reference feature map is SHA-256 based and avoids Python's process-randomized hash. Runners capture the source config, config digest, seed, Python/NumPy/platform versions, UTC creation time, real/synthetic flag, and network-download flag. Result manifests connect plots to their JSON source. Repeating a fixed-seed evaluation is tested for exact equality.

For a real experiment, additionally record git commit and dirty status, base/tokenizer/adapter hashes, trainer and policy hashes, optimizer/scheduler state, minibatch order, PRNG state, precision, kernel/backend/driver build, deterministic-operator setting, device/Android build, thermal/governor/charging state, dataset license and split digests, probe-generation digest, attack configuration, failures, and manual interventions.

Bitwise counterfactual equality may be unavailable on mobile accelerators. Declare a numerical tolerance and behavioral probe criterion before execution if deterministic kernels cannot be enabled; in that case do not label the result as exact under the theorem's premise.
