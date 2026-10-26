# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged

from odoo.addons.quick_create_governance.models.quick_create_rule import WILDCARD


@tagged("post_install", "-at_install", "quick_create_governance")
class TestQuickCreateRule(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Rule = cls.env["quick.create.rule"]
        cls.partner_model = cls.env["ir.model"]._get("res.partner")
        cls.users_model = cls.env["ir.model"]._get("res.users")

        def field(model, name):
            return cls.env["ir.model.fields"]._get(model, name)

        cls.f_parent = field("res.partner", "parent_id")
        cls.f_category = field("res.partner", "category_id")
        cls.f_title = field("res.partner", "title")
        cls.f_name = field("res.partner", "name")
        cls.f_user_company = field("res.users", "company_id")
        cls.group_exempt = cls.env["res.groups"].create({"name": "QCR Exempt"})
        # Start from a blank slate (e.g. demo rules), rolled back after the class.
        cls.Rule.search([]).write({"active": False})

    def setUp(self):
        super().setUp()
        # ormcache survives the test-transaction rollback: start and end clean.
        self.Rule.clear_caches()
        self.addCleanup(self.Rule.clear_caches)

    # helpers -----------------------------------------------------------
    def _rule(self, fields=(), **vals):
        vals.setdefault("model_id", self.partner_model.id)
        vals["field_ids"] = [(6, 0, [f.id for f in fields])]
        return self.Rule.create(vals)

    def _map(self, groups=()):
        return self.Rule._compile_restriction_map(tuple(sorted(g.id for g in groups)))

    # compilation -------------------------------------------------------
    def test_01_specific_fields(self):
        self._rule([self.f_parent, self.f_category])
        partner_map = self._map()["res.partner"]
        expected = {"create": True, "create_edit": True}
        self.assertEqual(partner_map["parent_id"], expected)
        self.assertEqual(partner_map["category_id"], expected)
        self.assertNotIn("title", partner_map, "Unconfigured fields must stay native")
        self.assertNotIn(WILDCARD, partner_map)

    def test_02_wildcard_when_no_field(self):
        self._rule(block_create_edit=False)
        self.assertEqual(self._map()["res.partner"],
                         {WILDCARD: {"create": True, "create_edit": False}})
        self.assertEqual(self.Rule._get_field_restriction("res.partner", "title"),
                         {"create": True, "create_edit": False})

    def test_03_rules_merge_with_or(self):
        self._rule([self.f_parent], block_quick_create=True, block_create_edit=False)
        self._rule([self.f_parent], block_quick_create=False, block_create_edit=True)
        self.assertEqual(self._map()["res.partner"]["parent_id"],
                         {"create": True, "create_edit": True})

    def test_04_wildcard_and_specific_combine_in_lookup(self):
        self._rule(block_create_edit=False)                       # whole model: Create
        self._rule([self.f_parent], block_quick_create=False)     # parent: Create and edit
        self.assertEqual(self.Rule._get_field_restriction("res.partner", "parent_id"),
                         {"create": True, "create_edit": True})
        self.assertEqual(self.Rule._get_field_restriction("res.partner", "title"),
                         {"create": True, "create_edit": False})
        self.assertIsNone(self.Rule._get_field_restriction("res.users", "company_id"))

    def test_05_inactive_rule_ignored(self):
        rule = self._rule([self.f_parent])
        rule.active = False
        self.assertNotIn("res.partner", self._map())

    def test_06_exempt_group(self):
        self._rule([self.f_parent], exempt_group_ids=[(6, 0, self.group_exempt.ids)])
        self.assertIn("res.partner", self._map())
        self.assertNotIn("res.partner", self._map([self.group_exempt]))

    def test_07_exemption_is_per_rule(self):
        self._rule([self.f_parent], exempt_group_ids=[(6, 0, self.group_exempt.ids)])
        self._rule([self.f_category])
        partner_map = self._map([self.group_exempt])["res.partner"]
        self.assertNotIn("parent_id", partner_map)
        self.assertIn("category_id", partner_map)

    # constraints -------------------------------------------------------
    def test_10_field_of_other_model_rejected(self):
        with self.assertRaises(ValidationError):
            self._rule([self.f_user_company])

    def test_11_non_relational_field_rejected(self):
        with self.assertRaises(ValidationError):
            self._rule([self.f_name])

    def test_12_must_block_something(self):
        with self.assertRaises(ValidationError):
            self._rule([self.f_parent], block_quick_create=False, block_create_edit=False)

    def test_13_name_and_scope(self):
        rule = self._rule([self.f_parent], block_create_edit=False)
        self.assertIn(self.partner_model.name, rule.name)
        self.assertIn(self.f_parent.field_description, rule.name)
        self.assertTrue(rule.scope_summary)
        self.assertIn(self.partner_model.name, self._rule().name)

    # cache -------------------------------------------------------------
    def test_20_cache_invalidated_on_write_and_unlink(self):
        rule = self._rule([self.f_parent])
        self.assertTrue(self._map()["res.partner"]["parent_id"]["create"])
        rule.block_quick_create = False
        self.assertFalse(self._map()["res.partner"]["parent_id"]["create"])
        rule.field_ids = [(6, 0, self.f_category.ids)]
        self.assertEqual(set(self._map()["res.partner"]), {"category_id"})
        rule.unlink()
        self.assertEqual(self._map(), {})

    def test_21_warm_cache_costs_no_query(self):
        self._rule([self.f_parent])
        key = (self.group_exempt.id,)
        self.Rule._compile_restriction_map(key)          # warm-up
        with self.assertQueryCount(0):
            for _i in range(100):
                self.Rule._compile_restriction_map(key)

    def test_22_session_payload_is_isolated_copy(self):
        self._rule([self.f_parent])
        payload = self.Rule._get_session_restrictions()
        payload["res.partner"]["parent_id"]["create"] = False
        payload.pop("res.partner")
        self.assertTrue(self.Rule._get_session_restrictions()["res.partner"]["parent_id"]["create"],
                        "Callers must not be able to corrupt the cached map")

    def test_23_session_payload_uses_current_user_groups(self):
        self._rule([self.f_parent], exempt_group_ids=[(6, 0, self.group_exempt.ids)])
        user = self.env["res.users"].create({
            "name": "QCR User", "login": "qcr_user",
            "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
        })
        Rule_as_user = self.Rule.with_user(user)
        self.assertIn("res.partner", Rule_as_user._get_session_restrictions())
        user.groups_id = [(4, self.group_exempt.id)]
        self.assertNotIn("res.partner", Rule_as_user._get_session_restrictions())

    def test_24_model_deletion_cascades(self):
        """ondelete='cascade' on model_id keeps the map free of dead models."""
        field = self.Rule._fields["model_id"]
        self.assertEqual(field.ondelete, "cascade")
