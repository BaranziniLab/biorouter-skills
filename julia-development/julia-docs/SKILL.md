---
name: julia-docs
description: "Read Julia documentation from the command line with `jldocs`, at the exact versions a project uses - the Julia manual, docstrings of Base, the standard libraries and the project's packages, their names, and where their methods are defined. Use before searching the web for anything about a Julia function, type, macro, module or package, when writing or fixing Julia code, or when a Julia name's behaviour, keyword arguments or exports are in doubt."
license: Apache-2.0 AND MIT
user-invocable: true
metadata:
  version: "1.0.0"
  origin: "adapted"
  upstream: "JuliaLang/DocBrowser.jl/skills/julia-docs@0146653c42f926e309c4b1739479ad54fc0f9694"
  upstream_licence: "MIT"
---

<!-- Adapted for Biorouter from JuliaLang/DocBrowser.jl (skills/julia-docs, commit 0146653c42f9), MIT. Changes: frontmatter rewritten for Biorouter; text kept. See LICENSE-UPSTREAM. -->

# Julia documentation with jldocs

`jldocs` prints the pages of DocBrowser.jl as plain text. Its answers match the Julia
version and the package versions of the project, and need no network, so prefer it to the web
and to memory for anything about Julia names.

If `jldocs` is not on the `PATH`, look in `~/.julia/bin`. Otherwise install it with
`julia -e 'using Pkg; Pkg.Apps.add(url="https://github.com/JuliaLang/DocBrowser.jl")'`,
or, in an environment that has DocBrowser, use `julia --project -m DocBrowser` in its place.

## Commands

Run them in the project's directory, or pass `--project PATH`.

- `jldocs find <words>`: names, and sections of Julia's manual and of the manuals of the
  project's packages, that match, best first, one a line. Each line starts with something
  `show` takes, and a section of a manual ends with its file. `--text` also searches the text
  of docstrings and manuals, which is done anyway when nothing else matches.
- `jldocs show <query>`: one page. A query is a name (`Base.sort!`, `DataFrames.select`),
  a module (`Base.Iterators`), a place in Julia's manual (`manual/arrays#Broadcasting`,
  `stdlib/Random`, `base/sort`), or a page of a package's manual
  (`GLMakie/explanations/figure#The-px_per_unit-factor`). `show manual` lists the pages of
  Julia's manual, and `show GLMakie/` those of a package's. The first line gives the version
  the page is about.
- `jldocs names <module>`: the names of a module, by kind, and whether each is exported
  or public. `--internal` adds the others.
- The exit code is 0 for an answer, 1 when nothing was found, and 2 for a mistake in the
  command, such as an option it does not take.

## Reading pages without wasting context

- For a long page, such as a manual chapter, run `show <query> --outline` first. It lists the
  numbered headings. Then `show <query> --section N` gives only that part.
- For a function with many docstrings or a very long one, `show <query> --brief` gives the
  signature and first paragraph of each docstring. When the docstrings come from several
  modules, as when a package adds a method to a function of `Base`, each starts with a
  `From Module:` line, and the outline says which one each heading is in.
- A package's page says how many pages its manual has, and `--outline` lists them.
- Links in a page end in a number, as in `sortslices[2]`. The `Links:` list at the end gives
  what each number leads to, in a form `show` takes, and for a page of a manual, its file.
- Each page's `Path:` line gives the file it comes from: the Markdown of a manual page, or the
  source file and line of a docstring. `find` gives the file of each manual section too. These
  are local files of the installed versions, so read or search them directly, for example with
  `grep`, when that is quicker than more `show` commands.
- A docstring page ends with its methods and the file and line where each is defined. Read
  that file when the docstring does not answer the question.

## Packages that are not loaded

The project's packages are not loaded by default, because loading runs their code. Until then,
`show` gives what the package's source documents, such as its README and manual, and `find`
does not see its names, which it says. Add `--load` to `show`, `find` or `names` to load the
package, or with `find` all of the project's packages, and read their docstrings. Only do this
for packages the project already depends on.

What is loaded also decides what a function's page shows: `show Base.sort` gives Base's
docstrings, and `show DataFrames.sort --load` adds the method that DataFrames documents.
