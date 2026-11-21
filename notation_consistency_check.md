# Notation Consistency Check

- `e_i` is always an event; `x_i` is its payload; `Prov(e_i)` is its envelope.
- `M_t` is memory state; `theta_t` is the promoted adapter state; candidate adapters use `q_k`.
- `W_k` is a training window and is not reused as a weight matrix; a generic base weight uses `W` only in the LoRA definition.
- `G_t` is avoided for the graph; the graph consistently uses calligraphic `G` (`\Graph`). Gradient bound uses scalar `G` only inside Proposition 1.
- `R_t`/`R` is a revocation set; `Desc_G(R)` is its descendant closure.
- `C_S`, `C_T`, and `C_E` consistently denote storage, elapsed-time, and energy costs.
- Every symbol in theorem statements is defined before use or locally quantified.
- LoRA dimensions are consistent: `A` is r-by-d_i, `B` is d_o-by-r, and `BA` matches `W`.
- The influence bound has parameter units; the storage bound has byte units.
- Label scan: 52 unique labels; no duplicate label warning in the final compile.
- Cross-reference scan after compilation: no unresolved reference warning.
