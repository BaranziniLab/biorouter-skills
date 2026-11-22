<!-- From timholy/claude_config CLAUDE.md, section "Julia style guide" (MIT). -->

# Julia style guide

- avoid being unnecessarily restrictive about method arguments. `f(A::Matrix{Float64})`
  silently excludes sparse matrices, GPU arrays, `Float32`, dual numbers, and anything
  else that would work fine — the caller gets a confusing `MethodError` instead.
  Annotate only as specifically as the implementation requires: use `Matrix{Float64}`
  only when a `ccall` or similar demands a specific memory layout and element type;
  use `AbstractMatrix` when 2-D structure matters; use `AbstractArray` when it does
  not; leave unannotated when the method works for any input. Annotate to control
  dispatch and resolve ambiguities, not to document intent.

- the same caution applies to parametric `struct` constructors. Write the inner
  constructor with *unconstrained* value arguments — `MyStruct{A,B}(a, b) where {A,B}`,
  not `(a::A, b::B)` — and let the field declarations and `new` do the
  coercion; constraining the arguments breaks calls like `MyStruct{Float64}(1, 0)`.
  Outer constructors should only compute type parameters and delegate inward,
  forming a cascade `MyStruct(args...)` → `MyStruct{A}(args...)` →
  `MyStruct{A,B}(args...)` so every call form coerces identically. Some
  `struct`s have trailing type-parameters that are primarily internal,
  conferring inferrability but not usually manipulated by users; the cascade should
  leap over these by calling the inner constructor directly,
  `MyStruct{A,B}(args...)` → `MyStruct{A,B,typeof(c),typeof(d)}(args...)`, where
  `c` and `d` have already been `convert`ed to types consistent with `A` and
  `B`, e.g., `c = convert(AbstractArray{A}, c)::AbstractArray{A}` given
  `C<:AbstractArray{A}`.

- avoid redundant keyword syntax: when a variable name matches the keyword argument
  name, use the short form `f(; max_iter)` instead of `f(; max_iter=max_iter)`.
  This applies at function call sites, `NamedTuple` construction, and similar contexts.
  Exception: packages supporting Julia before 1.6 must use the long form.

- `@test_throws SomeExceptionType expr` may be worth testing when
  `SomeExceptionType` provides meaning, but
  `@test_throws "message that clearly explains the problem to users" expr` is
  typically the more relevant target for testing. There are cases where it may
  be reasonable test both.
