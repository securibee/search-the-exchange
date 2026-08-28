# search-the-exchange

Checks the [CyberAgents Exchange](https://exchange.tenable.com) for something that already does
this, so you can use what's already been built instead of building it yourself. Say what you
want in whatever words you have: "best risk-based VM solution?", "tired of triaging phishing by
hand", "anything for cloud misconfigs?" It searches the catalog and returns a table of the
closest listings, each linked to its Exchange page, with a coverage verdict.

It does not interview you first. It infers what you meant, states that reading in the report so you
can correct it, and searches.

The catalog holds roughly 100 listings across `agents/`, `skills/`, `mcp-servers/`, and
`playbooks/`.

It runs on its own when you ask, and it is the network-facing half of
[`finding-security-friction`](https://github.com/securibee/finding-security-friction), which calls it
at its coverage gate so that "build this" is never recommended for something the Exchange already
has.

## What it does

1. Reads your request as a job shape: what goes in, what runs, what comes out. It infers this from
   plain speech rather than asking you to restate it. A bare noun is searched as a broad query, not
   bounced back as a question.
2. Strips identifiers from the query before anything leaves the machine.
3. Shallow-clones the content repository and builds the index locally, about a second, recording
   the catalog revision it read.
4. Reads the ~30KB index of all ~100 listings whole, then reads the full body of only the
   shortlisted candidates. The whole catalog is considered; nothing is sampled.
5. Assigns one verdict: **covered**, **partial**, **adjacent**, or **none**, matching on the job
   rather than on shared vocabulary.
6. Reports as a table, with every listing linked to its page on exchange.tenable.com.

## What it outputs

A header line for the query, the catalog revision, and the verdict. Then a table with one row per
matched listing: verdict, linked name, type, what it actually does, and the gap, ordered
covered → partial → adjacent. Then a one-line next step.

Every listing links to `https://exchange.tenable.com/<type>/<slug>/`. GitHub URLs never appear in
the report. The Exchange page is the entry point, and it links onward to the source repository.

A **none** verdict still gets the table, populated with the nearest listings and why each fell
short, so it is distinguishable from a search that never ran.

## Where a "no" leads

The point of a **none** verdict is that the thing is worth building. So the next step names the
official submission path rather than leaving you at a dead end:
[CyberAgents Exchange Submit](https://exchange.tenable.com/skills/cyberagents-exchange-submit/), the
Exchange's own skill for submitting agents, skills, MCP servers, and playbooks. It gets named for a
**partial** or **adjacent** verdict too, whenever you decide to build past the gap. This skill never
writes its own submission instructions.

Every report, not just a **none** one, ends with the same invitation to
[the Exchange Discord](https://exchange.tenable.com/discord): get help, share what you're building,
and hear what's landing next. Finding the listing you needed is as good a reason to be in the room as
finding nothing. It is also where to take a verdict you disagree with, since matching is a judgement
call and the catalog's maintainers settle it better than the skill can.

## How the catalog gets read

The content repository is the source. `tenable/cyberagents-exchange` publishes every listing as
markdown; the JSON API that would replace this is still in progress, so nothing here depends on it.

A shallow clone plus `tools/build-index.py` takes about a second, and `git rev-parse` reads the
revision out of the clone, so the revision reported provably matches the bytes searched. The tarball
works too when `git` is missing, at the cost of a separate call for the revision.

That is the only path. The index is built per run and never mirrored, so there is no stale copy to
serve and no fetch-only fallback to keep honest. A harness that cannot run commands cannot run this
skill. Nothing walks the catalog page by page either. Listing pages are 41KB of HTML each and there
are about 100 of them, which is where "it takes forever" came from.

The two files it writes are `listings.json` (metadata for every listing) and `listings-full.json`
(the same rows plus each listing's "What it does" and "How it works"). They use a schema deliberately
identical to the Exchange's own in-progress `/api/listings.json` and `/api/listings-full.json`: same
envelope, same keys, same singular `type`. When those endpoints ship, the skill fetches two URLs
instead of cloning, and that is also when it starts working without a shell.

To build the index by hand:

```bash
git clone --depth 1 https://github.com/tenable/cyberagents-exchange /tmp/xc
python3 tools/build-index.py /tmp/xc --rev "$(git -C /tmp/xc rev-parse --short HEAD)" --out-dir /tmp
```

## Prerequisites

- A shell, with `git` (or `curl` for the tarball) and `python3` for the index builder. There is no
  fetch-only path.
- Network access to GitHub.
- No authentication. The content repository is public.

## Install

```bash
git clone https://github.com/securibee/search-the-exchange.git
```

Then follow the section for your platform. `<repo>` is the absolute path to your clone.

### Claude Code

```bash
ln -s <repo> ~/.claude/skills/search-the-exchange
```

Run `/search-the-exchange` in a new session.

### Codex

Add to `AGENTS.md`:

```markdown
## Searching the exchange

When asked whether something already exists in the CyberAgents Exchange, a skill, agent, MCP
server, or playbook to use, extend, or check before building something new, read
`<repo>/SKILL.md` and follow it.
```

### Cursor

Create `.cursor/rules/search-the-exchange.mdc`:

```markdown
---
description: Check the CyberAgents Exchange for something that already does this, to use or before building
globs:
alwaysApply: false
---

Read <repo>/SKILL.md and follow it.
```

### Cline

Create `.clinerules/search-the-exchange.md`:

```markdown
When asked whether something already exists in the CyberAgents Exchange, to use it, extend it,
or check before building something new, read `<repo>/SKILL.md` and follow it.
```

### Gemini CLI

Add to `GEMINI.md`:

```markdown
## Searching the exchange

When asked to check the CyberAgents Exchange for something that already does this, to use it,
extend it, or before building something new, read `<repo>/SKILL.md` and follow it.
```

### Windsurf

Create `.windsurf/rules/search-the-exchange.md`:

```markdown
---
trigger: model_decision
description: Check the CyberAgents Exchange for something that already does this, to use or before building
---

Read <repo>/SKILL.md and follow it.
```

## What leaves the machine

One thing: the description of the work, with identifiers stripped, used to search a catalog fetched
over HTTPS. The fetch is a public, unauthenticated read of one GitHub repository. Nothing is posted
anywhere, and no evidence, hostnames, client names, credentials, engagement scope, ticket keys, file
paths, or quoted history is sent, including when a calling skill supplies them by mistake. In that
case they are dropped.

## Known limitations

- **The verdict rests on the listing, not the code.** Listings describe themselves; a listing can
  overstate what its linked repository does. The report says so, and offers to open the linked
  repository for the stronger check.
- **The catalog is a moving target.** Every report names the revision and build date, so an answer
  can be dated. The index is rebuilt from a fresh clone on every run, so it is never staler than the
  search itself.
- **A shell is required.** The catalog is cloned and indexed with `git` and `python3`, so harnesses
  without command execution, such as Claude Desktop or claude.ai, cannot run this skill until the
  Exchange's `/api/` endpoints ship and the clone becomes a fetch.
- **A failed fetch is not a "no".** "Nothing matched" is a finding only when the whole catalog was
  read; if the fetch fails the skill says the fetch failed.
- **Matching is a judgement call.** Free-form tags and prose descriptions mean two listings that do
  the same job may share no vocabulary. The skill matches on the job, but a genuinely novel framing
  of an existing idea can still slip past.
- **Exchange only.** Something that already does this elsewhere on GitHub, or in other skill
  catalogs, is out of scope. A **none** verdict means nothing in this catalog does the job, not
  that nobody has built it.

## License

MIT. See [LICENSE](LICENSE).
