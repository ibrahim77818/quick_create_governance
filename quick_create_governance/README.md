# Quick Create Governance (Odoo 18, Community & Enterprise)

Centrally remove **Create** and/or **Create and edit...** from many2one / many2many
widgets, per model and per field.

## Configure
*Settings → Users & Companies → Quick Create Governance*

| Field | Meaning |
|---|---|
| Model | Model hosting the field (e.g. `sale.order.line`) |
| Fields | many2one / many2many fields of that model. **Empty = all relational fields** |
| Block "Create" | Removes `Create "<text>"` from the dropdown (and the m2o confirmation dialog) |
| Block "Create and edit..." | Removes `Create and edit...`, the **New** button of the *Search More...* dialog, and creation in many2many "Add a line" dialogs |
| Exempt Groups | Members of any listed group are not affected by the rule |

Several rules on the same model/field are merged with OR (most restrictive wins).
Rules reach users at login / page reload (use **Apply Now (Reload)** to refresh your own client).

## How it works
1. `quick.create.rule._compile_restriction_map(group_ids)` builds
   `{model: {field | "*": {create, create_edit}}}`, **ORM-cached** per group set,
   invalidated (on every worker) by any create / write / unlink of a rule.
2. `ir.http.session_info()` ships that map as `session.quick_create_restrictions`.
   Warm cache = 0 SQL queries; no RPC is ever added to dropdown interactions.
3. JS patches (`static/src/js`) resolve the restriction once per field mount and
   strip capabilities **after** core evaluated XML options:
   * `Many2OneField` (+ every subclass: avatar, partner, list/kanban m2o, Studio...)
   * `Many2ManyTagsField` (+ subclasses) and many2many `X2ManyField` dialogs
   * `Many2XAutocomplete` safety net (filters any creation entry still present)

Governance is subtractive only: it never re-enables creation that the view
(`no_create`, `no_create_edit`, `no_quick_create`, `can_create`, Studio) disabled,
and XML/Studio cannot re-enable creation on a governed field.

**Scope note:** this is UI governance. Users with create rights on the target
model can still create records through its own menu, imports or RPC; use access
rights / record rules for hard security.

## Tests
```bash
odoo-bin -d test_db -i quick_create_governance --test-tags /quick_create_governance --stop-after-init
```
* `tests/test_quick_create_rule.py` – compilation, OR merge, wildcard, exemptions,
  constraints, cache invalidation, zero-query warm cache, payload isolation.
* `tests/test_ui.py` – session payload over JSON-RPC + two browser tours
  (requires Chrome): governed m2o / m2m tags / partial rule / Search More dialog,
  ungoverned native behaviour, XML `no_create` preserved, exempt group, and a
  100 000-lookup latency budget.
