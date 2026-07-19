# Teach Winter AI Something New

Drop `.txt` or `.md` files in this folder and Winter AI loads them automatically.

## Two ways to add knowledge

**Permanent (recommended):** Add the file here, commit to git, push.
It is loaded on every deploy forever.

**Live without redeploying:** POST to `/api/v1/teach/upload` (multipart `file` field).
Searchable immediately but disappears on the next Render redeploy unless you also commit it to git.

After uploading live, call `POST /api/v1/teach/reload` to re-scan without restart.

## Format

Plain text works. For trilingual answers use this format:

```
EN: The mitochondria is the powerhouse of the cell.
FR: La mitochondrie est la centrale energetique de la cellule.
RW: Mitochondria ni isoko ry ingufu mu ngirangingo.
```

Or pipe-separated on one line:
```
EN: hello | FR: bonjour | RW: muraho
```

Untagged lines are treated as English by default.
