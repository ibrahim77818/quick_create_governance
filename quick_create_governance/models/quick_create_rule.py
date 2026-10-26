# -*- coding: utf-8 -*-
import copy

from odoo import api, fields, models
from odoo.exceptions import ValidationError

RELATIONAL_TYPES = ("many2one", "many2many")
#: Key used in the compiled map when a rule targets every relational field.
WILDCARD = "*"


class QuickCreateRule(models.Model):
    """One governance rule: on ``model_id`` (optionally limited to
    ``field_ids``), remove the quick "Create" option and/or the
    "Create and edit..." paths from relational widgets.

    Several rules on the same model are merged with a logical OR: the most
    restrictive combination always wins.
    """

    _name = "quick.create.rule"
    _description = "Quick Create Governance Rule"
    _order = "model_name, sequence, id"
    # Odoo 20: the ORM clears this ormcache on every create / write / unlink
    # (and signals the other workers), replacing the manual CRUD overrides.
    _clear_cache_name = "default"

    name = fields.Char(compute="_compute_name", store=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
        index=True,
        help="Model whose form / list views host the relational fields to govern.",
    )
    model_name = fields.Char(
        related="model_id.model", string="Technical Model", store=True, index=True
    )
    field_ids = fields.Many2many(
        "ir.model.fields",
        "quick_create_rule_field_rel",
        "rule_id",
        "field_id",
        string="Fields",
        domain="[('model_id', '=', model_id), ('ttype', 'in', ('many2one', 'many2many'))]",
        help="Many2one / many2many fields to restrict. "
             "Leave empty to restrict every relational field of the model.",
    )
    block_quick_create = fields.Boolean(
        string='Block "Create"',
        default=True,
        help='Removes the "Create <typed text>" option from the dropdown.',
    )
    block_create_edit = fields.Boolean(
        string='Block "Create and edit..."',
        default=True,
        help='Removes "Create and edit..." from the dropdown and the "New" '
             'button of the "Search More..." selection dialog.',
    )
    exempt_group_ids = fields.Many2many(
        "res.groups",
        "quick_create_rule_group_rel",
        "rule_id",
        "group_id",
        string="Exempt Groups",
        help="Members of any of these groups are not affected by this rule.",
    )
    scope_summary = fields.Char(string="Scope", compute="_compute_scope_summary")
    note = fields.Text()

    # ------------------------------------------------------------------
    # Computes / onchanges / constraints
    # ------------------------------------------------------------------
    @api.depends("model_id.name", "field_ids.field_description")
    def _compute_name(self):
        for rule in self:
            if not rule.model_id:
                rule.name = self.env._("New rule")
                continue
            targets = ", ".join(rule.field_ids.mapped("field_description"))
            rule.name = "%s / %s" % (rule.model_id.name, targets or self.env._("All relational fields"))

    @api.depends("field_ids", "block_quick_create", "block_create_edit")
    def _compute_scope_summary(self):
        for rule in self:
            blocked = []
            if rule.block_quick_create:
                blocked.append(self.env._("Create"))
            if rule.block_create_edit:
                blocked.append(self.env._("Create and edit"))
            fields_txt = (
                self.env._("%s field(s)") % len(rule.field_ids)
                if rule.field_ids else self.env._("all relational fields")
            )
            rule.scope_summary = self.env._("%(actions)s blocked on %(fields)s") % {
                "actions": " + ".join(blocked) or self.env._("Nothing"),
                "fields": fields_txt,
            }

    @api.onchange("model_id")
    def _onchange_model_id(self):
        self.field_ids = self.field_ids.filtered(lambda f: f.model_id == self.model_id)

    @api.constrains("model_id", "field_ids")
    def _check_field_ids(self):
        for rule in self:
            wrong = rule.field_ids.filtered(
                lambda f: f.model_id != rule.model_id or f.ttype not in RELATIONAL_TYPES
            )
            if wrong:
                raise ValidationError(self.env._(
                    "Rule '%(rule)s': the following fields are not many2one / many2many "
                    "fields of model %(model)s: %(fields)s",
                    rule=rule.name,
                    model=rule.model_id.model,
                    fields=", ".join(wrong.mapped("name")),
                ))

    @api.constrains("block_quick_create", "block_create_edit")
    def _check_block_flags(self):
        for rule in self:
            if not (rule.block_quick_create or rule.block_create_edit):
                raise ValidationError(self.env._(
                    "Rule '%s' must block at least one action "
                    '("Create" or "Create and edit...").', rule.name
                ))

    def action_reload_client(self):
        """Rules reach a user's browser on the next page load; this reloads
        the current admin's web client so the change is visible at once."""
        self.env.transaction.invalidate_ormcache("default")
        return {"type": "ir.actions.client", "tag": "reload"}

    # ------------------------------------------------------------------
    # Compilation
    # ------------------------------------------------------------------
    @api.model
    @api.ormcache("group_ids")
    def _compile_restriction_map(self, group_ids):
        """Build ``{model: {field_or_*: {"create": bool, "create_edit": bool}}}``
        for a user belonging to ``group_ids`` (sorted tuple, part of the cache
        key). The result is cached until a rule changes; never mutate it."""
        user_groups = set(group_ids)
        result = {}
        rules = self.sudo().with_context(active_test=True).search([])
        for rule in rules:
            if user_groups.intersection(rule.exempt_group_ids.ids):
                continue
            model_map = result.setdefault(rule.model_name, {})
            for fname in rule.field_ids.mapped("name") or [WILDCARD]:
                entry = model_map.setdefault(fname, {"create": False, "create_edit": False})
                entry["create"] = entry["create"] or rule.block_quick_create
                entry["create_edit"] = entry["create_edit"] or rule.block_create_edit
        return result

    @api.model
    def _get_session_restrictions(self):
        """Restriction map for the current user, ready to be serialised in
        the web client session info."""
        # Odoo 19: group_ids holds explicit groups only; implied ones live in all_group_ids.
        group_ids = tuple(sorted(self.env.user.all_group_ids.ids))
        return copy.deepcopy(self._compile_restriction_map(group_ids))

    @api.model
    def _get_field_restriction(self, model_name, field_name):
        """Server-side mirror of the JS lookup (used by tests / integrators).
        Returns ``None`` when the field is not governed."""
        model_map = self._get_session_restrictions().get(model_name) or {}
        specific = model_map.get(field_name)
        wildcard = model_map.get(WILDCARD)
        if not specific and not wildcard:
            return None
        specific = specific or {}
        wildcard = wildcard or {}
        return {
            "create": bool(specific.get("create") or wildcard.get("create")),
            "create_edit": bool(specific.get("create_edit") or wildcard.get("create_edit")),
        }
