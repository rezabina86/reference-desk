---
description: Rebuild the knowledge site and publish the public half to reza-bina.com/notes
allowed-tools: Bash(cd:*), Bash(./publish.sh:*), Bash(git:*), Bash(python3:*)
---

Publish the reference desk. Work in `~/Developer/knowledge`.

Run `./publish.sh`. It rebuilds the private site, rebuilds the public one into
`docs/` and into `~/Developer/reza-bina.com/public/notes/index.html`, refuses to
continue if anything private leaked into the public build, then commits and pushes
both repos.

The day sessions quote an employment contract and a CV. They are excluded by
`.gitignore` and by `"private": true` on the daily topic, and the script greps the
public build before committing. Never add `index.html`, `topics/daily/`, or any day
session to a commit, and never run `git add -f` on a path the ignore file covers.
If the leak check fires, stop and show me the offending line rather than working
around it.

Handle these three failures without asking me:

- **The site repo is on a branch other than `main`.** Tell me which branch, and ask
  before switching — I may have work in progress there.
- **`git push` is rejected because `main` moved.** `git pull --rebase` and push again.
  The only file the script touches in that repo is `public/notes/index.html`, which is
  generated, so a conflict in it is resolved by rebuilding: rerun `./publish.sh`.
- **A stale `.git/*.lock` file.** Check that no other git process is running, then
  delete the lock and retry once.

When it is done, report in two lines: the commit subject that landed in each repo,
and the GitHub Actions run URL for `rezabina86/reza-bina.com` (`gh run list --limit 1`),
so I can see when reza-bina.com/notes has the new build. Do not open a pull request —
these are generated-file commits and go straight to `main`.
